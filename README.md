# ferkee
Ferkee is a system that crawls the ferc.gov website for so-called "Notional Decisions" and alerts users when critical FERC decisions come down.

It currently consists of a mashup of a Scrapy-based web crawler (called Ferkee) controlled by a Perl script that runs in an event loop.

Configuration is controlled by the user-supplied -c argument to a standard properties file.  See the sample_ferkee.props file as an example. At a minimum you have to provide SMTP mail information for sending email alerts.

Running Ferkee:

`    ./ferkee.pl -c PROPS_FILE_LOCATION`

where "PROPS_FILE_LOCATION" is your properties file.

Runtime dependencies are shown below:

- perl 5.18
	- CPAN
	- JSON::Parse
	- Config::Properties
- python 2.7.x
- Scrapy 1.4
- sendemail 1.5x

AWS Linux Raw Install
=============================

This is quick and dirty minimal install.  Some steps are specific to AWS Linux AMI only

# Install CPAN
sudo yum install perl-CPAN make gcc

# Install JSON::Parse Perl module
sudo cpan JSON::Parse

# Install Config::Properties Perl module
sudo cpan Config::Properties

# Install Scrapy
sudo pip install scrapy

# Install sendemail
curl http://caspian.dotconf.net/menu/Software/SendEmail/sendEmail-v1.56.tar.gz -o sendEmail.tar.gz
gunzip sendEmail.tar.gz
tar -xvf sendEmail.tar

sudo yum install perl-Crypt-SSLeay-0.64
sudo yum install perl-IO-Socket-SSL-1.94

Patch sendEmail.pl line 1906 - comment out line, add in line below as shown here:

  # if (! IO::Socket::SSL->start_SSL($SERVER, SSL_version => 'SSLv3 TLSv1')) {
  if (! IO::Socket::SSL->start_SSL($SERVER)) {


#Install PDFMiner
See https://pypi.python.org/pypi/pdfminer/
Download source, run setup.py install

# Tar up Ferkee
ferkee/bin/archiveFerkee
sftp -i yourkey.pem user@server 
sftp> put ferkee.tar



