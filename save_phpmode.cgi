#!/usr/local/bin/perl
# Save PHP options options for a virtual server

require './virtual-server-lib.pl';
&ReadParse();
&error_setup($text{'phpmode_err2'});
$d = &get_domain($in{'dom'});
&can_edit_domain($d) || &error($text{'edit_ecannot'});
$can = &can_edit_phpmode($d);
$canv = &can_edit_phpver($d);
$can || $canv || &error($text{'phpmode_ecannot'});
&require_apache();
$p = &domain_has_website($d);
@modes = &supported_php_modes($d);
$newmode = $in{'mode'};
if ($can) {
	# Check for option clashes
	if (!$d->{'alias'} && $can) {
		if (defined($in{'children_def'}) && !$in{'children_def'} &&
		    ($in{'children'} < 1 ||
		     $in{'children'} > $max_php_fcgid_children)) {
			&error(&text('phpmode_echildren', $max_php_fcgid_children));
			}
		}
	if (!$d->{'alias'}) {
		if (defined($in{'maxtime_def'}) && !$in{'maxtime_def'} &&
		    $in{'maxtime'} !~ /^[1-9]\d*$/ && $in{'maxtime'} < 86400) {
			&error($text{'phpmode_emaxtime'});
			}
		}

	# Check for working Apache suexec for PHP
	if (!$d->{'alias'} && ($newmode eq 'cgi' || $newmode eq 'fcgid') &&
	    $can && $p eq 'web') {
		$tmpl = &get_template($d->{'template'});
		$err = &check_suexec_install($tmpl);
		&error($err) if ($err);
		}
	}

# Start telling the user what is being done
&ui_print_unbuffered_header(&domain_in($d), $text{'phpmode_title2'}, "");
&obtain_lock_web($d);
&obtain_lock_dns($d);
&obtain_lock_logrotate($d) if ($d->{'logrotate'});
$mode = $oldmode = &get_domain_php_mode($d);

if ($can) {
	# Save PHP execution mode
	if (defined($newmode) && $oldmode ne $newmode && $can) {
		&$first_print(&text('phpmode_moding', $text{'phpmode_'.$newmode}));
		if (&indexof($newmode, @modes) < 0) {
			&$second_print($text{'phpmode_emode'});
			}
		else {
			my $err = &save_domain_php_mode($d, $newmode);
			if ($err) {
				&$second_print(&text('phpmode_emoding', $err));
				}
			else {
				&$second_print($text{'setup_done'});
				$mode = $newmode;
				}
			}
		$anything++;
		}

	# Save PHP fcgi children
	$nc = $in{'children_def'} ? 0 : $in{'children'};
	if (defined($in{'children_def'}) &&
	    $nc != &get_domain_php_children($d) && $can) {
		&$first_print($nc || $mode eq "fpm" ?
		    &text('phpmode_kidding', $nc || &get_php_max_childred_allowed()) :
		    $text{'phpmode_nokids'});
		&save_domain_php_children($d, $nc);
		&$second_print($text{'setup_done'});
		$anything++;
		}

	# Save max PHP run time (in both Apache and PHP configs)
	$max = $in{'maxtime_def'} ? 0 : $in{'maxtime'};
	$oldmax = $mode eq "fcgid" ? &get_fcgid_max_execution_time($d)
				   : &get_php_max_execution_time($d);
	if (defined($in{'maxtime_def'}) &&
	    $oldmax != $max) {
		&$first_print($max ? &text('phpmode_maxing', $max)
				   : $text{'phpmode_nomax'});
		&set_fcgid_max_execution_time($d, $max);
		&set_php_max_execution_time($d, $max);
		&$second_print($text{'setup_done'});
		$anything++;
		}
	}

# Update PHP versions
@avail = &list_available_php_versions($d, $mode);
if ($canv && !$d->{'alias'} && $mode && $mode ne "mod_php" &&
    @avail > 1 && ($oldmode eq $mode ||
                   ($oldmode eq 'cgi' && $mode eq 'fcgid') ||
                   ($oldmode eq 'fcgid' && $mode eq 'cgi'))) {
	my %enabled = map { $_, 1 } split(/\0/, $in{'d'});
	my $phd = &public_html_dir($d);
	for(my $i=0; defined($in{"dir_".$i}); $i++) {
		my $sd = $in{"dir_".$i};
		$sd =~ s/^\Q$phd\E\///;
		if (!$enabled{$i} && $i != 0) {
			# This directory can be disabled
			&$first_print(&text('phpmode_deldir',
				"<tt>".&html_escape($sd)."</tt>"));
			if ($in{"dir_".$i} ne $phd) {
				&delete_domain_php_directory($d, $in{"dir_".$i});
				&$second_print($text{'setup_done'});
				$anything++;
				}
			else {
				&$second_print($text{'phpmode_edeldir'});
				}
			}
		elsif ($in{"ver_$i"} ne $in{"oldver_$i"}) {
			# Directory version can be updated
			&$first_print(&text('phpmode_savedir',
				"<tt>".&html_escape($sd)."</tt>",
				$in{"ver_$i"}));
			$err = &save_domain_php_directory(
				$d, $in{"dir_$i"}, $in{"ver_$i"});
			&error($err) if ($err);
			&$second_print($text{'setup_done'});
			$anything++;
			}
		}
	if ($enabled{'new'}) {
		# Directory to add
                $in{'dir_new'} =~ /^[^\/]\S+$/ ||
                        &error($text{'phpver_enewdir'});
                $in{'dir_new'} =~ /^(http|https|ftp):/ &&
                        &error($text{'phpver_enewdir'});
		&$first_print(&text('phpmode_adddir',
			"<tt>".&html_escape($in{"dir_new"})."</tt>",
			$in{'ver_new'}));
                $err = &save_domain_php_directory(
			$d, $phd."/".$in{'dir_new'}, $in{'ver_new'});
                &error($err) if ($err);
		&$second_print($text{'setup_done'});
		$anything++;
		}
	}

# PHP log
if (defined($in{'plog_def'})) {
	my $oldplog = &get_domain_php_error_log($d);
	my $plog;
	if ($in{'plog_def'} == 1) {
		# Logging disabled
		$plog = undef;
		}
	elsif ($in{'plog_def'} == 2) {
		# Use the default log
		$plog = &get_default_php_error_log($d);
		}
	else {
		# Custom path
		$plog = $in{'plog'};
		if ($plog && $plog !~ /^\//) {
			$plog = $d->{'home'}.'/'.$plog;
			}
		$plog =~ /^\/\S+$/ || &error($text{'phpmode_eplog'});
		}
	if ($plog ne $oldplog) {
		&$first_print($text{'phpmode_setplog'});
		$err = &save_domain_php_error_log($d, $plog);
		&$second_print(!$err ? $text{'setup_done'}
				     : &text('phpmode_logerr', $err));
		$anything++;
		if ($newmode eq 'cgi' || $newmode eq 'fcgid') {
			if ($p eq "web") {
				&register_post_action(\&restart_apache);
				}
			elsif ($p) {
				&plugin_call($p, "feature_restart_web_php", $d);
				}
			}
		}
	}

if (!$anything) {
	&$first_print($text{'phpmode_nothing'});
	&$second_print($text{'phpmode_nothing_skip'});
	}

&save_domain($d);
&refresh_webmin_user($d);
&release_lock_logrotate($d) if ($d->{'logrotate'});
&release_lock_dns($d);
&release_lock_web($d);
&clear_links_cache($d);
&run_post_actions();

# Call any theme post command
if (defined(&theme_post_save_domain)) {
	&theme_post_save_domain($d, 'modify');
	}

# All done
&webmin_log("phpmode", "domain", $d->{'dom'});
&ui_print_footer("edit_phpmode.cgi?dom=$d->{'id'}", $text{'edit_php_return'},
                 &domain_footer_link($d),
		 "", $text{'index_return'});

