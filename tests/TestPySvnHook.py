# -*- coding: utf-8 -*-
 
import os, sys, unittest, cStringIO, re

sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..' ) )
from PySvnHooks import PySvnHook, PreCommitHook, PostCommitHook

TEST_ROOT = os.path.abspath( os.path.dirname( __file__ ) )
TEST_REPO = os.path.join( TEST_ROOT, 'PySvnHookTestRepo' )

class MockTwitterer( object ):
    def __init__( self ):
        self.called_tweet = []
    
    def tweet( self, text=None, dm_at_user=None):
        self.called_tweet.append( {
            'message':  text,
            'dm':       dm_at_user
        } )

class MockEmailer( object ):
    def __init__( self ):
        self.called_email = []
    
    def email( self, to, message ):
        self.called_email.append( {
            'message':  message,
            'to':       to
        } )

class MockTinyizer( object ):
    def __init__( self ):
        self.called_tinyize = []
    
    def tinyize( self, url ):
        self.called_tinyize.append( {
            'url':  url
        } )

class TestPySvnHook( unittest.TestCase ):
    STDERR = sys.stderr
    STDOUT = sys.stdout
    def setUp( self ):
        sys.stderr      = cStringIO.StringIO()
        self.emailer    = MockEmailer()
        self.twitterer  = MockTwitterer()
        self.tinyizer   = MockTinyizer()
        
    def tearDown( self ):
        sys.stderr = self.STDERR
    
    def assertContains( self, haystack, needle ):
        self.assert_( haystack.find( needle ) != -1, '""""%s""" does not contain """%s"""' % ( haystack, needle ) )
    
    def generatePreCommit( self, revision ):
        return PreCommitHook( repository=TEST_REPO, revision = revision, twitterer=self.twitterer, emailer=self.emailer, tinyizer=self.tinyizer )
    
    def generatePostCommit( self, revision ):
        return PostCommitHook( repository=TEST_REPO, revision = revision, twitterer=self.twitterer, emailer=self.emailer, tinyizer=self.tinyizer )
    
    def testDevBranchWithoutTicket( self ):
        """
            Revision 0 commits a file outisde the production root
            without a Ticket in the commit message
        """
        "Precommit hook shouldn't throw any warnings"
        tmp = self.generatePreCommit( 1 )
        self.assertEqual( tmp.run_tests(), None )
        self.assertEqual( tmp._err.getvalue(), '' )
        
        "Postcommit hook should throw a warning, and return an error code of 1."
        tmp = self.generatePostCommit( 1 )
        self.assertEqual( tmp.run_tests(), 1 )
        self.assertContains( tmp._err.getvalue(), 'COMMIT WARNING' )
    
    def testProdBranchWithoutTicket( self ):
        tmp = self.generatePreCommit( 3 )
        self.assertEqual( tmp.run_tests(), 1 )
        self.assertContains( tmp._err.getvalue(), 'COMMIT FAILURE' )
    
    def testDevBranchTwitterWithoutDm( self ):
        tmp = self.generatePostCommit( 1 )
        tmp.run_tests()
        self.assertEqual( len( self.twitterer.called_tweet ), 0 )
    
    def testTwitterWithDm( self ):
        tmp = self.generatePostCommit( 2 ) # Commit 2 should send to @mikewest
        tmp.run_tests()
        self.assertEqual( len( self.twitterer.called_tweet ), 1 )
        self.assertContains( self.twitterer.called_tweet[0]['message'], 'would like you to take a look at revision #2' )
        self.assertEqual( self.twitterer.called_tweet[0]['dm'], 'mikewest' )

    def testEmail( self ):
        tmp = self.generatePostCommit( 2 ) # Commit 2 should send to @mikewest
        tmp.run_tests()
        self.assertEqual( len( self.emailer.called_email ), 1 )
        self.assertContains( self.emailer.called_email[0]['message'], 'committed revision #2 to SVN, and thinks you might be interested in the changeset' )
        self.assertEqual( self.emailer.called_email[0]['to'], ['mike@mikewest.org'] )
    
    def testStaticAccessControl( self ):
        tmp = self.generatePreCommit( 4 )
        self.assertEqual( tmp.run_tests(), 1 )
        self.assertContains( tmp._err.getvalue(), 'COMMIT FAILURE' )
    
if __name__ == '__main__':
    unittest.main()