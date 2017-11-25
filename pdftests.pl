#!/usr/bin/perl

use strict;
use warnings;

my $url = shift (@ARGV);
print "$url\n";

my @urlParts = split ("/", $url);
my $fileName = $urlParts[scalar (@urlParts)-1];

`curl -O $url`;

my @pdf2text = `pdf2txt.py -t text $fileName`;

my $i = 0;

for my $line (@pdf2text) {
  chomp ($line);
  next if !$line;
  last if $i > 40;
  if ($line =~ /^[2I]\./) {
    last;
  }
  print "$line\n";
  $i++;
}
unlink $fileName;

