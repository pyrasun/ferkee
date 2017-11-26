#!/usr/bin/perl

use strict;
use warnings;
use JSON::Parse 'json_file_to_perl';

my $crawlResult = json_file_to_perl ("/tmp/ferkee_result.json");

$crawlResult = $crawlResult->[0];

print ("Notional Decision URL: $crawlResult->{'url'}\n");

my @decisions = $crawlResult->{'decisions'}; 

for my $decisionArray (@decisions) {
  my $decision = $decisionArray->[0];
  my $docket = $decision->{'docket'};
  my $decisionURL = $decision->{'decisionUrl'};
  print ("\tDocket $docket, Decision $decisionURL\n");
}

