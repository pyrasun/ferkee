#!/usr/bin/perl

use strict;
use warnings;

use Getopt::Std;
use Config::Properties;
use JSON::Parse 'json_file_to_perl';

our ($opt_c, $opt_i, $opt_n);
getopt("cin");

my @version = `cat version.txt`;
print "$version[0]\n";

print "Loading config $opt_c\n";
die "Properties file not found: $opt_c" if (!-f $opt_c);

my $config = Config::Properties->new(file => $opt_c);
print "Config $opt_c loaded\n";

my $to = $config->getProperty("to");
my $from = $config->getProperty("from");
my $adminTo = $config->getProperty("admin_to");
my $from_p = $config->getProperty("from_p");
my $decisionPattern = $config->getProperty("decision_pattern");
my $sendMail = 1;
if ($opt_n) {
   $sendMail = 0;
}

print "Options: to:$to, from:$from, adminTo=$adminTo, decision_pattern=$decisionPattern, sendMail=$sendMail\n";

my $notionalDecisionURL = "";
my %seenDecisions = ();

if ($opt_i) {
	print ("Ignoring saved state\n");
} else {
	print "Reading ferkeeState.txt...\n";
	&readState();
}

print "Entering bot loop\n";
# &sendAlert($to, "Ferkee $version[0] started", "Ferkee has been restarted and is now live. You will be emailed FERC pipeline decision orders in realtime\n\nTo unsubscribe send an email to ferkeebot\@gmail.com\n");

while (1) {

	print "=========================================================\n";
	my $now = `date`;
	print "Running bot $now\n";
  my $docketAlert = "";
  my $adminAlert = "";

  # Fire Ferkee bot!
	unlink "/tmp/ferkee_result.json";
  my @lines = `scrapy crawl ferkee >ferkee.log 2>&1`;

	next if !-f "/tmp/ferkee_result.json";

	my $crawlResult = json_file_to_perl ("/tmp/ferkee_result.json");
	$crawlResult = $crawlResult->[0];
	my $thisNotionalDecisionURL = $crawlResult->{'url'};
	print ("Notional Decision URL: $thisNotionalDecisionURL\n");
  if ($thisNotionalDecisionURL ne $notionalDecisionURL) {
    $notionalDecisionURL = $thisNotionalDecisionURL;
    $adminAlert .= "A new Notional Decision page has been published: $notionalDecisionURL\n";
    %seenDecisions = ();
  }

	my $decisions = $crawlResult->{'decisions'}; 

  # Loop through our decisions and grab the ones that match our alerting pattern
	for my $decision (@$decisions) {
		my $docket = $decision->{'docket'};
		my $url = $decision->{'decisionUrl'};
		print ("\tDocket $docket, Decision $url\n");
		next if !($docket =~ /$decisionPattern/);
		if (!$seenDecisions{$docket}) {
			$docketAlert .= "***************  New Certificate Pipeline Decision: $docket: $url\n";
			$seenDecisions{$docket} = $url;
			$docketAlert .= &getDecisionText($url) . "\n\n";
		}
	}

  # Send admin alerts
  if ($adminAlert) {
		&sendAlert($adminTo, "Ferkee Admin Notice", $adminAlert);
  }

  # Send docket alerts (CP decisions)
  if ($docketAlert) {
		&sendAlert($to, "Ferkee Alert!  Certificate Pipeline Decision Published", $docketAlert);
  }

  &dumpState();
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

sub dumpState() {
  open FERKEE_STATE, ">ferkeeState.txt";
  print FERKEE_STATE "$notionalDecisionURL\n";

  while(my ($docket, $url) = each %seenDecisions) {
    print FERKEE_STATE "$docket;$url\n";
  }

  close FERKEE_STATE;
}

sub readState() {
  if (!-f "ferkeeState.txt") {
    print "No ferkeeState.txt found, first run\n";
    return;
  }
  open (FERKEE_STATE, "ferkeeState.txt");
  my @lines = <FERKEE_STATE>;
  $notionalDecisionURL = shift(@lines);
  chomp($notionalDecisionURL);
  foreach my $decision (@lines) {
    chomp ($decision);
    my ($docket, $url) = split (";", $decision);
    chomp ($docket);
    chomp ($url);
    $seenDecisions{$docket} = $url;
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

