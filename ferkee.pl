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
      $docketAlert .= "New Certificate Pipeline Decision: $docket: $url\n";
      $decisions{$docket} = $url;
    }
  }

  # Send admin alerts
  if ($adminAlert) {
    print $adminAlert;

    if ($sendMail) {
      my $subject = "Ferkee Admin Notice";

      open SENDEMAIL, "|sendemail -f $from -t $adminTo -u '$subject' -s smtp.gmail.com:587 -xu $from -xp '$from_p'";
      print  SENDEMAIL "$adminAlert\n";
      close(SENDEMAIL);
    }
  }

  # Send docket alerts (CP decisions)
  if ($docketAlert) {
    print $docketAlert;

    if ($sendMail) {
      my $subject = "Ferkee Alert!  Certificate Pipeline Decision Published";

      open SENDEMAIL, "|sendemail -f $from -t $to -u '$subject' -s smtp.gmail.com:587 -xu $from -xp '$from_p'";
      print  SENDEMAIL "$docketAlert\n";
      close(SENDEMAIL);
    }
  }

  &dumpState();
  sleep (60);
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

