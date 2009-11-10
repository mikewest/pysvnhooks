# -*- coding: utf-8 -*-
import os, sys, re, urllib, urllib2, base64, socket, smtplib
from subprocess import Popen, PIPE
import settings

if os.path.exists( os.path.join( '/usr', 'local', 'bin', 'svnlook' ) ):
    SVNLOOK = os.path.join( '/usr', 'local', 'bin', 'svnlook' )
else:
    SVNLOOK = os.path.join( '/usr', 'bin', 'svnlook' )

socket.setdefaulttimeout( 3 ) # If a connection takes more than 3 seconds, abandon it.

class Twitterer( object ):
    def tweet( self, text=None, dm_at_user=None):
        username = settings.TWITTER_USERNAME
        password = settings.TWITTER_PASSWORD
        url      = 'http://twitter.com/statuses/update.json'
        
        base64string    = base64.encodestring( '%s:%s' % (username, password) )[ :-1 ]
        authheader      =  "Basic %s" % base64string
        
        if dm_at_user is not None:
            url     = 'http://twitter.com/direct_messages/new.json'
            data    = urllib.urlencode( { 'user': dm_at_user, 'text': text })
        else:
            data    = urllib.urlencode( { 'status' : text } )
        
        req     = urllib2.Request( url, data )
        req.add_header("Authorization", authheader)
        handle  = urllib2.urlopen(req)

class Emailer( object ):
    def email( self, to, message ):
        try:
            server = smtplib.SMTP( 'localhost' )
            server.sendmail( settings.EMAIL_FROM_ADDRESS, to, message )
            server.quit()
            return True
        except smtplib.SMTPException:
            return False
            
class Tinyizer( object ):
    def __init__( self ):
        self._tiny = {}
        
    def tinyize( self, url ):
        if not self._tiny.has_key( url ):
            tiny    = 'http://is.gd/api.php?longurl=%s' % urllib.quote( url )
            try:
                self._tiny[ url ] = urllib.urlopen( tiny ).read()
            except Exception:
                self._tiny[ url ] = url
        return self._tiny[ url ]

class PySvnHook( object ):
    """Base class for PreCommitHook and PostCommitHook"""
    #
    #   Some helpful class constants
    #
    COMPRESSION_BOT     = settings.HEADLESS_USERNAME
    TICKET_REGEX        = re.compile( r'[a-zA-Z]+-\d+'    )
    PRODUCTION_REGEX    = re.compile( r'/production/'  )
    STATICS_REGEX       = re.compile( r'/statics/'     )
    NONSDE_REGEX        = re.compile( r'/(flashdevelopment|orm)/' )
    VIEWER_URL          = settings.VIEWER_URL
    VALID_RECIPIENTS    = settings.VALID_RECIPIENTS
    COMMIT_EMAIL_LIST   = settings.COMMIT_EMAIL_LIST
    
    def __init__( self, repository = None, txn_name = None, revision = None, twitterer = None, emailer = None, tinyizer = None ):
        self._repo      = repository
        self._txn       = txn_name
        self._rev       = revision
        if self._rev is not None:
            self._rev = int( self._rev )
        self._err       = sys.stderr
        self._log       = self.look( 'log' ).strip()
        self._author    = self.look( 'author' ).strip()
        self._dirs      = self.look( 'dirs-changed' ).strip().split( '\n' )
        self._tiny      = tinyizer or Tinyizer()
        self._twitterer = twitterer or Twitterer()
        self._emailer   = emailer or Emailer()
        
    def run_tests( self ):
        return 0
    
    def error( self, message ):
        self._err.write( message )
        return 1
    
    def look( self, cmd ):
        """
            Wrapper for the `svnlook` command.  Runs `svnlook CMD`, and passes
            in either the provided transaction name or revision.
        """
        if self._txn is not None:
            result, errors = Popen( [ SVNLOOK, cmd, '-t', self._txn, self._repo ], stdout=PIPE ).communicate()
        elif self._rev is not None:
            result, errors = Popen( [ SVNLOOK, cmd, '-r %d' % self._rev, self._repo ], stdout=PIPE ).communicate()
        
        if errors:
            self._err.write( errors )
            sys.exit( 1 )
        return result
    
    def tweet( self, text=None, dm_at_user=None):
        self._twitterer.tweet( text=text, dm_at_user=dm_at_user )
    
    def email( self, to, message ):
        self._emailer.email( to=to, message=message )
    
    def tinyize( self, url ):
        return self._tiny.tinyize( url=url )
    
    #
    #   Bug-based helpers
    #
    def is_tied_to_bug( self ):
        return PySvnHook.TICKET_REGEX.search( self._log )
    
    ##########################################################################
    #
    #   Path-based helpers
    #    
    def is_path( self, path_regex ):
        dirs = [ path for path in self._dirs if path_regex.search( path ) ]
        return ( dirs != [] )

    def is_production( self ):
        return self.is_path( PySvnHook.PRODUCTION_REGEX )
   
    def is_only_sde( self ):
        return not self.is_path( PySvnHook.NONSDE_REGEX )

    def is_static( self ):
        return self.is_path( PySvnHook.STATICS_REGEX)

##############################################################################
#
#   PreCommitHook
#
class PreCommitHook( PySvnHook ):
    """Tests to be run on `pre-commit`"""
    #
    #   Test Runner
    #
    def run_tests( self ):
        return (
                self.is_log_nonempty()
            or  self.is_sde_change_not_tied_to_bug()
            or  self.is_headless_user_authorized()
        )

    #
    #   Test definitions
    #
    def is_log_nonempty( self ):
        if re.match( r'^$', self._log ):
            return self.error( """
#####################################################################
#   COMMIT FAILURE                                                  #
#                                                                   #
#   Your commit message must not be empty.  Please enter something  #
#   descriptive so that we have half a chance of understanding what #
#   your changes mean.  :)                                          #
#                                                                   #
#####################################################################
            """)

    def is_sde_change_not_tied_to_bug( self ):
        if self.is_only_sde() and not self.is_tied_to_bug():
            return self.error( """
#####################################################################
#   COMMIT FAILURE                                                  #
#                                                                   #
#   Your commit message must contain at least one reference to a    #
#   Jira ticket in the format `[JIRATYPE-ID]` (e.g. "Fixing         #
#   [FRONT-123]")' ).  If you aren't work on on a Jira ticket, go   #
#   create one!  Or, if a ticket is _really_ unnecessary, please    #
#   use `[WWW-17]` our no-ticket ticket.                            #
#                                                                   #
#   Thanks!                                                         #
#                                                                   #
#####################################################################
            """)
    
    def is_headless_user_authorized( self ):
        if self.is_static() and not PySvnHook.COMPRESSION_BOT == self._author:
            return self.error( """
#####################################################################
#   COMMIT FAILURE                                                  #
#                                                                   #
#   The compression bot is the only user authorized to commit to    #
#   the statics directory.  If you need to adjust the CSS or JS,    #
#   then please simply edit the source files, and let the bot       #
#   automagically compress them after you commit your changes.      #
#                                                                   #
#####################################################################
            """)
            
        if not self.is_static() and PySvnHook.COMPRESSION_BOT == self._author:
            return self.error( """
#####################################################################
#   COMMIT FAILURE                                                  #
#                                                                   #
#   The compression bot is not authorized to commit anywhere other  #
#   than the designated statics directory.  Bad bot.                #
#                                                                   #
#####################################################################
            """)

##############################################################################
#
#   PreCommitHook
#
class PostCommitHook( PySvnHook ):
    """Tests to be run on `post-commit`"""
    #
    #   Test Runner
    #
    def run_tests( self ):
        errors =    self.is_commit_tied_to_bug()
        self.communicate()
        return ( errors )

    #
    #   Test definitions
    #
    def is_commit_tied_to_bug( self ):
        if not self.is_tied_to_bug():
            self.error("""
#####################################################################
#   COMMIT WARNING                                                  #
#                                                                   #
#   Your commit was saved successfully!  A quick note, however:     #
#                                                                   #
#   Your commit message doesn't reference any Jira ticket.  It'd be #
#   great if it did, as it simplifies the whole process of figuring #
#   out exactly what each commit aims at, and what changes fix what #
#   bugs.  It would be brilliant if you could take a minute or two  #
#   next time to make sure that a Jira ticket exists for the work   #
#   you're doing, and that it appears in your commit message (e.g.  #
#   "Fixed [WWW-14]")!                                              #
#                                                                   #
#   If your change is so small that you don't believe that it       #
#   requires a ticket, please mark it with "[WWW-17]", our          #
#   "no ticket" ticket.                                             #
#                                                                   #
#####################################################################
            """)
            return 0 
        return 0
    
    def communicate( self ):
        if self.is_production():
            self.post_to_twitter()
        
        has_        = lambda y, x: (self.VALID_RECIPIENTS.has_key( x ) and self.VALID_RECIPIENTS[ x ].has_key( y ) and self.VALID_RECIPIENTS[ x ][ y ] is not None)
        people      = re.findall( r'@([-a-zA-Z0-9_]+)', self._log )
        
        email_list  = [ self.VALID_RECIPIENTS[ person ][ 'email' ]   for person in people if has_( 'email', person ) ]
        dm_list     = [ self.VALID_RECIPIENTS[ person ][ 'twitter' ] for person in people if has_( 'twitter', person ) ]
        
        if self.COMMIT_EMAIL_LIST is not None:
            email_list.append( self.COMMIT_EMAIL_LIST )

        self.send_notification_emails( email_list )
        self.send_dms( dm_list )
        
    def send_notification_emails( self, email_list ):
        tinyurl = self.tinyize( PySvnHook.VIEWER_URL % self._rev )
        params  = {
                    'from':     settings.EMAIL_FROM_ADDRESS,
                    'repo':     os.path.basename( self._repo ),
                    'author':   self._author,
                    'rev':      self._rev,
                    'tinyurl':  tinyurl,
                    'log':      self._log,
                    'to_list':  ", ".join( email_list )
                  }
        message = """\
From: %(from)s
To: %(to_list)s
Subject: [%(repo)s] %(author)s committed r%(rev)d

Hello!  %(author)s committed r%(rev)d to SVN.  If you've got a minute, take a look:

---- COMMIT LOG --------------------------------------------------

%(log)s


* Details at: %(tinyurl)s

------------------------------------------------- /COMMIT LOG ----

Thanks for your attention!

-The Friendly SDE SVN Bot""" % ( params )

        self.email( to=email_list, message=message )
        
    def post_to_twitter( self ):
        tinyurl = self.tinyize( PySvnHook.VIEWER_URL % self._rev )
        
        author = self._author
        if self.VALID_RECIPIENTS.has_key( author ) and self.VALID_RECIPIENTS[ author ].has_key( 'twitter' ):
            author = '@%s' % self.VALID_RECIPIENTS[ author ][ 'twitter' ]
        
        message = "%s committed r%d to production: %s" % ( author, self._rev, tinyurl )
        self.tweet( message )
    
    def send_dms( self, dm_list ):
        tinyurl = self.tinyize( PySvnHook.VIEWER_URL % self._rev )
        
        author  = self._author
        if self.VALID_RECIPIENTS.has_key( author ) and self.VALID_RECIPIENTS[ author ].has_key( 'twitter' ):
            author = '@%s' % self.VALID_RECIPIENTS[ author ][ 'twitter' ]
        
        for dm in dm_list:
            message = "%s would like you to take a look at r%d: %s" % ( self._author, self._rev, tinyurl )
            self.tweet( message, dm )
