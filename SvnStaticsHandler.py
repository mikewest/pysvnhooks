# -*- coding: utf-8 -*-
 
import os, sys, re
import settings
from subprocess import Popen, PIPE

class Concatenater( object ):
    def concat( self, filelist, outfile ):
        outfile = open( outfile, 'w' )
        for cur in filelist:
            f = open( cur, 'r' )
            try:
                outfile.write( f.read() )
            finally:
                f.close()
        outfile.close()
    

class Minimizer( object ):
    def __init__( self, infile, outfile ):
        pass

class StaticsHandler( object ):
    USERNAME = settings.HEADLESS_USERNAME
    PASSWORD = settings.HEADLESS_PASSWORD
    def __init__( self ):
        pass
