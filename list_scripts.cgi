#!/usr/local/bin/perl
# Show available and installed scripts for this domain

require './virtual-server-lib.pl';
&ReadParse();
$d = &get_domain($in{'dom'});
&can_edit_domain($d) && &can_edit_scripts() || &error($text{'edit_ecannot'});
$d->{'web'} && $d->{'dir'} || &error($text{'scripts_eweb'});
@got = &list_domain_scripts($d);

&ui_print_header(&domain_in($d), $text{'scripts_title'}, "", "scripts");
@allscripts = map { &get_script($_) } &list_scripts();
@scripts = grep { $_->{'avail'} } @allscripts;
%smap = map { $_->{'name'}, $_ } @allscripts;

# Start tabs for listing and installing
@tabs = ( [ "existing", $text{'scripts_tabexisting'},
	    "list_scripts.cgi?dom=$in{'dom'}&scriptsmode=existing" ],
	  [ "new", $text{'scripts_tabnew'},
	    "list_scripts.cgi?dom=$in{'dom'}&scriptsmode=new" ] );
if (&can_unsupported_scripts()) {
	push(@tabs, [ "unsup", $text{'scripts_tabunsup'},
		      "list_scripts.cgi?dom=$in{'dom'}&scriptsmode=unsup" ] );
	}
print &ui_tabs_start(\@tabs, "scriptsmode",
	$in{'scriptsmode'} ? $in{'scriptsmode'} : @got ? "existing" : "new", 1);

# Build table of installed scripts (if any)
print &ui_tabs_start_tab("scriptsmode", "existing");
@table = ( );
$ratings = &get_script_ratings();
$upcount = 0;
foreach $sinfo (sort { lc($smap{$a->{'name'}}->{'desc'}) cmp
		       lc($smap{$b->{'name'}}->{'desc'}) } @got) {
	# Check if a newer version exists
	$script = $smap{$sinfo->{'name'}};
	@vers = grep { &can_script_version($script, $_) }
		     @{$script->{'versions'}};
	if (&indexof($sinfo->{'version'}, @vers) < 0) {
		@better = grep { &compare_versions($_, $sinfo->{'version'}) > 0 } @vers;
		if (@better) {
			$status = "<font color=#ffaa00>".
			  &text('scripts_newer', $better[$#better]).
			  "</font>";
			$upcount++;
			}
		else {
			$status = $text{'scripts_nonewer'};
			}
		}
	else {
		$status = "<font color=#00aa00>".
			  $text{'scripts_newest'}."</font>";
		}
	$path = $sinfo->{'opts'}->{'path'};
	($dbtype, $dbname) = split(/_/, $sinfo->{'opts'}->{'db'}, 2);
	if ($dbtype && $dbname && $script->{'name'} !~ /^php(\S+)admin$/i) {
		$dbdesc = &text('scripts_idbname2',
		      "edit_database.cgi?dom=$in{'dom'}&type=$dbtype&".
			"name=$dbname",
		      $text{'databases_'.$dbtype}, "<tt>$dbname</tt>");
		}
	elsif ($sinfo->{'opts'}->{'db'}) {
		# Just a DB name, perhaps for a script that can only
		# use a single type
		$dbdesc = "<tt>$sinfo->{'opts'}->{'db'}</tt>";
		}
	else {
		$dbdesc = "<i>$text{'scripts_nodb'}</i>";
		}
	$desc = $script->{'desc'};
	if ($sinfo->{'partial'}) {
		$desc = "<i>$desc</i>";
		}
	push(@table, [
		{ 'type' => 'checkbox', 'name' => 'd',
		  'value' => $sinfo->{'id'} },
		"<a href='edit_script.cgi?dom=$in{'dom'}&".
		 "script=$sinfo->{'id'}'>$desc</a>",
		$script->{'vdesc'}->{$sinfo->{'version'}} ||
		  $sinfo->{'version'},
		$sinfo->{'url'} ? 
		  "<a href='$sinfo->{'url'}' target=_new>$path</a>" :
		  $path,
		$dbdesc,
		$status,
		&virtualmin_ui_rating_selector(
			$sinfo->{'name'}, $ratings->{$sinfo->{'name'}},
			5, "rate_script.cgi?dom=$in{'dom'}")
		]);
	}

# Show table of scripts
if (@got) {
	print $text{'scripts_desc3'},"<p>\n";
	}
print &ui_form_columns_table(
	"mass_uninstall.cgi",
	[ [ "uninstall", $text{'scripts_uninstalls'} ],
	  $upcount ? ( [ "upgrade", $text{'scripts_upgrades'} ] ) : ( ) ],
	1,
	undef,
	[ [ "dom", $in{'dom'} ] ], 
	[ "", $text{'scripts_name'}, $text{'scripts_ver'},
	  $text{'scripts_path'}, $text{'scripts_db'},
	  $text{'scripts_status'}, $text{'scripts_rating'} ],
	100,
	\@table,
	undef,
	0,
	undef,
	$text{'scripts_noexisting'}
	);

print &ui_tabs_end_tab();

# Show table for installing scripts, by category
print &ui_tabs_start_tab("scriptsmode", "new");
@allscripts = @scripts;
if (@scripts) {
	# Show search form
	print &ui_form_start("list_scripts.cgi");
	print &ui_hidden("dom", $in{'dom'});
	print &ui_hidden("scriptsmode", "new");
	print "<b>$text{'scripts_find'}</b> ",
	      &ui_textbox("search", $in{'search'}, 30)," ",
	      &ui_submit($text{'scripts_findok'});
	print &ui_form_end();
	}

if ($in{'search'}) {
	# Limit to matches
	$search = $in{'search'};
	@scripts = grep { $_->{'desc'} =~ /\Q$search\E/i ||
			  $_->{'longdesc'} =~ /\Q$search\E/i ||
			  $_->{'category'} =~ /\Q$search\E/i } @scripts;
	}

# Build table of available scripts
@table = ( );
foreach $script (@scripts) {
	$script->{'sortcategory'} = $script->{'category'} ||
				    "zzz";
	}
$overall = &get_overall_script_ratings();
foreach $script (sort { $a->{'sortcategory'} cmp
				$b->{'sortcategory'} ||
			lc($a->{'desc'}) cmp lc($b->{'desc'}) }
		      @scripts) {
	$cat = $script->{'category'} || $text{'scripts_nocat'};
	@vers = grep { &can_script_version($script, $_) }
		     @{$script->{'versions'}};
	next if (!@vers);	# No allowed versions!
	if ($cat ne $lastcat && @scripts > 1) {
		# Start of new group
		push(@table, [ { 'type' => 'group',
				 'desc' => $cat } ]);
		$lastcat = $cat;
		}
	if (@vers > 1) {
		$vsel = &ui_select("ver_".$script->{'name'},
		    undef,
		    [ map { [ $_, $script->{'vdesc'}->{$_} ] }
			  @vers ]);
		}
	else {
		$vsel = ($script->{'vdesc'}->{$vers[0]} ||
			 $vers[0]).
			&ui_hidden("ver_".$script->{'name'},
				   $vers[0]);
		}
	$r = $overall->{$script->{'name'}};
	push(@table, [
	    { 'type' => 'radio', 'name' => 'script',
	      'value' => $script->{'name'},
	      'checked' => $in{'search'} && @scripts == 1 },
	    $script->{'desc'},
	    $vsel,
	    $script->{'longdesc'},
	    $r ? &virtualmin_ui_rating_selector(undef, $r, 5)
	       : "",
	    ]);
	}

# Show table of available scripts
print &ui_form_columns_table(
	"script_form.cgi",
	[ [ undef, $text{'scripts_ok'} ] ],
	0,
	undef,
	[ [ "dom", $in{'dom'} ] ],
	[ "", $text{'scripts_name'}, $text{'scripts_ver'},
	  $text{'scripts_longdesc'}, $text{'scripts_overall'} ],
	100,
	\@table,
	undef,
	0,
	undef,
	!@allscripts ? $text{'scripts_nonew'} : $text{'scripts_nomatch'}
	);

print &ui_tabs_end_tab();

# Show form for installing a non-standard version
if (&can_unsupported_scripts()) {
	print &ui_tabs_start_tab("scriptsmode", "unsup");
	print $text{'scripts_unsupdesc'},"<p>\n";
	print &ui_form_start("script_form.cgi");
	print &ui_hidden("dom", $in{'dom'}),"\n";
	print &ui_table_start($text{'scripts_unsupheader'}, undef, 2,
			      [ "width=30%" ]);

	# Script type
	print &ui_table_row($text{'scripts_unsupname'},
	   &ui_select("script", undef, 
	      [ map { [ $_->{'name'}, $_->{'desc'} ] }
		 sort { lc($a->{'desc'}) cmp lc($b->{'desc'}) } @scripts ]));

	# Version to install
	print &ui_table_row($text{'scripts_unsupver'},
		&ui_textbox("ver", undef, 15));

	print &ui_table_end();
	print &ui_form_end([ [ undef, $text{'scripts_ok'} ] ]);
	print &ui_tabs_end_tab();
	}

print &ui_tabs_end(1);

&ui_print_footer(&domain_footer_link($d),
		 "", $text{'index_return'});

