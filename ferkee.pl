#!/usr/bin/perl

use strict;
use warnings;

use Getopt::Std;
use Config::Properties;

our ($opt_c);
getopt("c");

print "Loading config $opt_c\n";
die "Properties file not found: $opt_c" if (!-f $opt_c);

my $config = Config::Properties->new(file => $opt_c);
print "Config $opt_c loaded\n";

my $to = $config->getProperty("to");
my $from = $config->getProperty("from");
my $adminTo = $config->getProperty("admin_to");
my $from_p = $config->getProperty("from_p");

print "Options: to:$to, from:$from, adminTo=$adminTo\n";

# my $to = "michael.spille\@gmail.com lorraine.crown\@yahoo.com";
my $sendMail = 1;
my $notionalDecisionURL = "";
my %decisions = ();

print "Reading ferkeeState.txt...\n";
&readState();

print "Entering bot loop\n";
while (1) {

  my $docketAlert = "";
  my $adminAlert = "";

  # Fire Ferkee bot!
  my @lines = `scrapy crawl ferkee 2>>ferkee.log`;

  # First line is the most recent notional decision file
  my $thisNotionalDecisionURL = shift(@lines);
  chomp ($thisNotionalDecisionURL);
  if ($thisNotionalDecisionURL ne $notionalDecisionURL) {
    $notionalDecisionURL = $thisNotionalDecisionURL;
    $adminAlert .= "A new Notional Decision page has been published: $notionalDecisionURL\n";
    %decisions = ();
  }

  # Loop through remaining lines - these are Certificate Pipeline (CP) decisions
  foreach my $decision (@lines) {
    chomp ($decision);
    my ($docket, $url) = split (";", $decision);
    chomp ($docket);
    chomp ($url);

    if (!$decisions{$docket}) {
      $docketAlert .= "***************  New Certificate Pipeline Decision: $docket: $url\n";
      $decisions{$docket} = $url;
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
		open SENDEMAIL, "|sendemail -f $from -t $to -u '$subject' -s smtp.gmail.com:587 -xu $from -xp '$from_p'";
		print  SENDEMAIL "$alert\n";
		close(SENDEMAIL);
	}

}

sub dumpState() {
  open FERKEE_STATE, ">ferkeeState.txt";
  print FERKEE_STATE "$notionalDecisionURL\n";

  while(my ($docket, $url) = each %decisions) {
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
    $decisions{$docket} = $url;
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

	my @pdf2text = `pdf2txt.py -t text $fileName`;

	my $i = 0;

	for my $line (@pdf2text) {
		chomp ($line);
		next if $line =~ /^\s$/;
		next if !$line;
		last if $i > 40;
		if ($line =~ /^[2I]\./) {
			last;
		}
		push (@text, "$line");
		$i++;
	}
	unlink $fileName;
	return join ("\n", @text);
}

