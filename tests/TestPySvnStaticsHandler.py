# -*- coding: utf-8 -*-
 
import os, sys, unittest, cStringIO, re

sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..' ) )
from SvnStaticsHandler import Concatenater

TEST_ROOT = os.path.abspath( os.path.dirname( __file__ ) )
TEST_DATA = os.path.join( TEST_ROOT, 'StaticsData' )

class TestConcatenater( unittest.TestCase ):
    def setUp( self ):
        self.result = os.path.join( TEST_DATA, 'result.data' )
        
    def tearDown( self ):
        os.remove( os.path.join( TEST_DATA, 'result.data' ) )
        
    def assertResultEquals( self, test ):
        tmp     = open( self.result, 'r' )
        self.assertEqual( tmp.read(), test )
    
    def testOneFile( self ):
        tmp     = Concatenater()
        files   = [ os.path.join( TEST_DATA, '1.data' ) ]
        tmp.concat( files, self.result )
        self.assertResultEquals( '1\n' )
        
    def testTwoFiles( self ):
        tmp     = Concatenater()
        
        files   = [ os.path.join( TEST_DATA, '%d.data' % num ) for num in range( 1, 3 ) ]
        tmp.concat( files, self.result )
        self.assertResultEquals( '1\n2\n' )
        
    def testOrdering( self ):
        tmp     = Concatenater()
        
        files   = [ os.path.join( TEST_DATA, '%d.data' % num ) for num in reversed( range( 1, 5 ) ) ]
        tmp.concat( files, self.result )
        self.assertResultEquals( '4\n3\n2\n1\n' )
        
if __name__ == '__main__':
    unittest.main()