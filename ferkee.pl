#!/usr/bin/perl

#
# TO DELETE SOON
# SUPERCEDED BY PURE PYTHON VERSION
# 

use strict;
use warnings;

use Getopt::Std;
use Config::Properties;
use JSON::Parse 'json_file_to_perl';
use JSON::Create 'create_json';

our ($opt_c, $opt_i, $opt_n);
getopt("cin");

my @version = `cat version.txt`;
print "$version[0]\n";

print "Loading config $opt_c\n";
die "Properties file not found: $opt_c" if (!-f $opt_c);

my $config = Config::Properties->new(file => $opt_c);
print "Config $opt_c loaded\n";

my $to = $config->getProperty("to");
my $noticeTo = $config->getProperty("noticeTo");
my $from = $config->getProperty("from");
my $adminTo = $config->getProperty("admin_to");
my $from_p = $config->getProperty("from_p");
my $decisionPattern = $config->getProperty("decision_pattern");
my $sendMail = 1;
if ($opt_n) {
   $sendMail = 0;
}

print "Options: to:$to, from:$from, adminTo=$adminTo, decision_pattern=$decisionPattern, sendMail=$sendMail\n";

my %seenDecisions = ();
my %seenNotices = ();

if ($opt_i) {
	print ("Ignoring saved state\n");
} else {
	print "Reading ferkeeState.txt...\n";
	&newReadState();
}

print "Entering bot loop\n";
# &sendAlert($to, "Ferkee $version[0] started", "Ferkee has been restarted and is now live. You will be emailed FERC pipeline decision orders in realtime\n\nTo unsubscribe send an email to ferkeebot\@gmail.com\n");

while (1) {

	print "=========================================================\n";
	my $now = `date`;
	print "Running bot $now\n";
  my $docketAlert = "";
  my $adminAlert = "";
  my $noticeAlert = "";

  # Fire Ferkee bot!
	unlink "/tmp/ferkee_result.json";
  my @lines = `scrapy crawl ferkee >ferkee.log 2>&1`;

	my $resultFile = "/tmp/ferkee_result.json";
	next if !-f $resultFile;
  next if (-s $resultFile == 0);

	my $crawlResult = json_file_to_perl ($resultFile);
  my $resultCount = 0;

  my $resultLen = scalar @$crawlResult;
  while ($resultCount < $resultLen) {
    my $result = $crawlResult->[$resultCount++];

    my $decisions = $result->{'decisions'}; 
    if ($decisions) {
      #
      # Process notional decisions (todo: Refactor into sub)
      #
      my $thisNotionalDecisionURL = $result->{'url'};
      print ("Notional Decision URL: $thisNotionalDecisionURL\n");

      # Loop through our decisions and grab the ones that match our alerting pattern
      for my $decision (@$decisions) {
        my $docket = $decision->{'docket'};
        my $url = $decision->{'decisionUrl'};
        print ("\tDocket $docket, Decision $url\n");
        next if !($docket =~ /$decisionPattern/);
        my $key = $thisNotionalDecisionURL . " - " . $docket;
        if (!$seenDecisions{$key}) {
          $docketAlert .= "***************  New Certificate Pipeline Decision: $docket: $url\n";
          $seenDecisions{$key} = $url;
          $docketAlert .= &getDecisionText($url) . "\n\n";
        }
      }
    } else {
      #
      # Process notices (todo: Refactor into sub)
      #
      my $thisNoticeURL = $result->{'url'};
      print ("Notice URL: $thisNoticeURL\n");

      my $notices = $result->{'notices'}; 
      for my $notice (@$notices) {
        my $dockets = $notice->{'dockets'};
        my $description = $notice->{'description'};
        my $urls = $notice->{'urls'};
        my $key = $thisNoticeURL . " - " . $dockets;
        if (!$seenNotices{$key}) {
          $noticeAlert .= "*************** FERC CP Notice or Delegated Order $dockets\n$description\n$urls\n\n";
          $seenNotices{$key} = $urls;
        }
      }
    }
  }

  # Send admin alerts
  if ($adminAlert) {
		&sendAlert($adminTo, "Ferkee Admin Notice", $adminAlert);
  } else {
    print "No Admin alerts\n";
  }

  # Send docket alerts (CP decisions)
  if ($docketAlert) {
		&sendAlert($to, "Ferkee Alert!  Certificate Pipeline Decision Published", $docketAlert);
  } else {
    print "No notional decision alerts\n";
  }

  # Send Notice alerts
  if ($noticeAlert) {
		&sendAlert($noticeTo, "Ferkee Alert!  FERC CP Notice(s) Isused", $noticeAlert);
  } else {
    print "No notice alerts\n";
  }

  &newDumpState();
  sleep (60);
}

sub sendAlert {
	my $to = shift (@_);
	my $subject = shift (@_);
	my $alert = shift (@_);

	`date`;
	print "$alert";
	if ($sendMail) {
		open SENDEMAIL, "|sendEmail -f $from -t $to -u '$subject' -s smtp.gmail.com:587 -xu $from -xp '$from_p'";
		print  SENDEMAIL "$alert\n";
		close(SENDEMAIL);
	}

}

sub newDumpState() {
  my %dumpVars = ("seenDecisions", \%seenDecisions, "seenNotices", \%seenNotices);
 
  my @state = (
    \%dumpVars,
  );
  my $json = create_json (\@state);
  open FERKEE_STATE, ">ferkeeState.json";
  print FERKEE_STATE $json;
  close FERKEE_STATE;
}

sub newReadState() {
  if (!-f "ferkeeState.json") {
    print "No ferkeeState.txt found, first run\n";
    return;
  }
	my $state = json_file_to_perl ("ferkeeState.json");
	my $result = $state->[0];

  my $savedDecisions = $result->{'seenDecisions'};
  for my $dkey (keys(%$savedDecisions)) {
    my $dvalue = $savedDecisions->{$dkey};
    $seenDecisions{$dkey} = $dvalue;
  }
  my $savedNotices = $result->{'seenNotices'};
  for my $nkey (keys(%$savedNotices)) {
    my $nvalue = $savedNotices->{$nkey};
    $seenNotices{$nkey} = $nvalue;
  }
}

sub getDecisionText {
	my $url = shift (@_);
	$url =~ s/http:/https:/;
	print "$url\n";

	my @text = ();

	my @urlParts = split ("/", $url);
	my $fileName = $urlParts[scalar (@urlParts)-1];

	`curl -O $url`;

	my @pdf2text = `pdf2txt.py -m 1 -t text -L 1.0 $fileName`;

	my $i = 0;

	for my $line (@pdf2text) {
		chomp ($line);
		next if $line =~ /^\s$/;
		next if !$line;
		# last if $i > 40;
		# if ($line =~ /^[2I]\./) {
		# 	last;
		# }
		push (@text, "$line");
		$i++;
	}
	unlink $fileName;
	return join ("\n", @text);
}

