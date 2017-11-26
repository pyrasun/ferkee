# ferkee
Ferkee is a system that crawls the ferc.gov website for so-called "Notional Decisions" and alerts users when critical FERC decisions come down.

It currently consists of a mashup of a Scrapy-based web crawler (called Ferkee) controlled by a Perl script that runs in an event loop.

Configuration is controlled by the user-supplied -c argument to a standard properties file.  See the sample_ferkee.props file as an example. At a minimum you have to provide SMTP mail information for sending email alerts.

Runtime dependencies:

perl 5.18
	CPAN
	JSON::Parse
	Config::Properties
python 2.7.x
Scrapy 1.4
sendemail 1.5x

