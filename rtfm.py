#!/usr/bin/python2.7
# Allright I know it should be python3
##
# Inspired by : https://xkcd.com/293/
# https://www.amazon.co.uk/Rtfm-Red-Team-Field-Manual/dp/1494295504
# Thanks for the Scaffolding Max!
##

import optparse
import re
import socket
import sys
import sqlite3
import os.path
import urllib
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL)

#########################################################################
# RTFM: Just Read the Friggin Manual
#########################################################################
#########################################################################
# Copyright: lololol
#########################################################################
__version__ =	"0.4.0"
__prog__ =	"rtfm"
__authors__ =	["See Referances: They are the real writers!"]

#########################################################################
## Flags cCtThHwvdiIus
## FIxes:
##  * Indexes on comments
##  * Probabley should use prepared statements : local so dont care
##  * Check for dupe tags
##  * Warn on dupe tags
##
## Pipeline:
##  * Swap to more sophisticated SQL, quite innefficent at the moment
##  * Populate referances table
##  * Search - Case sensitve versions : T and C
##  * Create a HTML page 	      : H
##  * create a WIKI format 	      : W
##  * Remark (comment)  Search	      : r
##  * Referance Search		      : R
##  * Drop to SQL Shell               : s
##  * Template engine(autofill [user] : A user=innes,pass=password,attacker=1.1.1.1,victim=2.2.2.2
##  * Make code more sane and betterize the layout
##
## Future:
##  * Cool Thing mode
##  * teach me mode
##  * Quiz me mode?
##  * Fix the typos
#########################################################################

#########################################################################
# XXX: Configuration
#########################################################################

EXIT_CODES = {
	"ok"	  : 0,
	"generic" : 1,
	"invalid" : 3,
	"missing" : 5,
	"limit"   : 7,
}

ANSI = {
	"white" : '\033[37m',
	"purple" : '\033[95m',
	"blue" : '\033[94m',
	"green" : '\033[92m',
	"yellow" : '\033[93m',
	"red" : '\033[91m',
	"bold" : '\033[1m',
	"reset" : '\033[0m'
}


#########################################################################
# XXX: Kick off
#########################################################################

def run():
	conn = None
	db_exists = os.path.exists('snips.db')
	if db_exists:
		conn = sqlite3.connect('snips.db')
		conn.text_factory=str
	else:
		err("Cant access the DB, you're on your own.")

	if options.update:
		Updater(conn)
	if (options.cmd is not None) and (options.tag is not None):
		SearchTagsnCmd(conn)
	elif options.tag is not None:
		SearchTags(conn)
	elif options.cmd is not None:
		SearchCommand(conn)
	elif options.insert is not None:
		Insert(conn)
	elif (options.dump):
		Dump(conn)
	else:
		err("RTFM: rtfm -h")

####
# Definitions
####
def Updater(conn):
	ok("This may appear to hang. Its due to my bad SQL, sorry, run with debug to get more info")
	icmd=[]
	itags=[]
	irefs=[]
	cur = conn.cursor()
	uplist = 'https://lg.lc/updates.txt'
	req = urllib.urlopen(uplist)    
	updates = req.read().splitlines()
	for line in updates:
		update = line.split(",")
		debug("S : SELECT * from tblUpdates where hash like '"+update[1]+"'")
		cur.execute("SELECT * from tblUpdates where hash like ?",(update[1],))
		row=cur.fetchall()
		if len(row) == 0:
			download=urllib.urlopen(update[2])
			downfile=download.read().splitlines()
			# TODO : DOWNLOAD VERIFICATION
			skipc=skipt=0
			for cmdline in downfile:
				if (cmdline not in ('EOC','')) and skipc == 0:
					icmd.append(cmdline)
					continue
				elif skipc ==0:
					skipc=1
					continue
				if (cmdline not in ('EOT','')) and skipt == 0:
					itags.append(cmdline)
					continue
				elif skipt == 0:
					skipt=1
					continue
				if (cmdline not in ('EOR','')):
					irefs.append(cmdline)
				else:
					skipc=skipt=0
					debug("Command : "+str(icmd))
					debug("Tags : "+str(itags))
					debug("Referances : "+str(irefs))
					newid=dbInsertCmdS(conn,icmd)
					dbInsertTags(conn,itags,newid)
					dbInsertRefs(conn,irefs,newid)
					icmd=[]
					itags=[]
					irefs=[]
					continue
			ok("Hopefully added lots of new commands")
			debug("I: INSERT INTO tblupdates values (NULL,"+update[1]+","+update[2]+",date('now')")
			cur.execute("INSERT INTO tblupdates values (NULL,?,?,date('now'))",(update[1],update[2]))
			conn.commit()
		else:
			debug("XXX Skipping Update : "+update[1])
		ok("Parsed Line")
	ok("Update complete")
	exit()

def dbInsertTags(conn,tags,id):
	cur = conn.cursor()
	for tag in tags:
		debug("S : SELECT tagid from tbltagcontent where tag like '"+tag+"'")
		cur.execute("SELECT Tagid FROM Tbltagcontent where tag like ?",(tag,))
		count=cur.fetchall()
		if len(count) > 1:
			err("More than one tag returned! "+str(count))
		elif len(count) is 1:
			debug("Tag found : "+str(count[0][0]))
			debug("I: INSERT INTO tbltagmap values ("+str(count[0][0])+","+str(id)+")")
			cur.execute("INSERT INTO tbltagmap values (NULL,?,?)",(str(count[0][0]),str(id)))
			conn.commit()
			ok("Added tags")
		elif len(count) is 0:
			debug("Tag not found in DB")
			debug("I: INSERT INTO tbltagcontent VALUES (NULL,'"+tag+"')")
			cur.execute("INSERT INTO tbltagcontent values (NULL,?)",(tag,))
			debug("We have added Tag : "+str(cur.lastrowid))
			debug("I: INSERT INTO tbltagmap values ("+str(cur.lastrowid)+","+str(id)+")")
			cur.execute("INSERT INTO tbltagmap values (NULL,?,?)",(cur.lastrowid,id))
			conn.commit()
			ok("Added a new tag and a tagmap")
		else:
			err("I dont know how you even got here, https://www.youtube.com/watch?v=dQw4w9WgXcQ")

def dbInsertRefs(conn,refs,id):
	cur = conn.cursor()
	for ref in refs:
		debug("S : SELECT id from tblrefcontent where ref like '"+ref+"'")
		cur.execute("SELECT id FROM Tblrefcontent where ref like ?",(ref,))
		count=cur.fetchall()
		if len(count) > 1:
			err("More than one ref returned! "+str(count))
		elif len(count) is 1:
			debug("Ref found : "+str(count[0][0]))
			debug("I: INSERT INTO tblrefmap values ("+str(count[0][0])+","+str(id)+")")
			cur.execute("INSERT INTO tblrefmap values (NULL,?,?)",(str(count[0][0]),str(id)))
			conn.commit()
			ok("Added Refs")
		elif len(count) is 0:
			debug("ref not found in DB")
			debug("I: INSERT INTO tblrefcontent VALUES (NULL,'"+ref+"')")
			cur.execute("INSERT INTO tblrefcontent values (NULL,?)",(ref,))
			debug("We have added Ref : "+str(cur.lastrowid))
			debug("I: INSERT INTO tblrefmap values ("+str(cur.lastrowid)+","+str(id)+")")
			cur.execute("INSERT INTO tblrefmap values (NULL,?,?)",(cur.lastrowid,id))
			conn.commit()
			ok("Added a new Ref and a refmap")
		else:
			err("I dont know how you even got here, https://www.youtube.com/watch?v=dQw4w9WgXcQ")

def dbInsertCmdS(conn,cmd):
	cur = conn.cursor()
	if (options.debug):
		debug("I: INSERT INTO tblcommand VALUES (NULL,'"+str(cmd[0])+"','"+str(cmd[1])+"',"+"date('now'))")
	cur.execute('INSERT INTO tblcommand VALUES (NULL,?,?,date("now"));',cmd)
	conn.commit()
	ok("Added Rows :"+str(cur.rowcount))
	return cur.lastrowid

def dbInsertCmd(conn,cmds):
	cur = conn.cursor()
	if (options.debug):
		for cmd in cmds:
			debug("I: INSERT INTO tblcommand VALUES (NULL,'"+str(cmd[0])+"','"+str(cmd[1])+"',"+"date('now'))")
	cur.executemany('INSERT INTO tblcommand VALUES (NULL,?,?,date("now"));',cmds)
	conn.commit()
	ok("Added Rows :"+str(cur.rowcount))

def Insert(conn):
	if options.insert is 't':
		tags=[]
		tag='EasterEgg'
		id=raw_input("What CMD are we adding tags to? : ")
		while tag != '':
			tag=raw_input("Enter a tag (blank for non) : ")
			if tag is not '':
				tags.append(tag)
		if (tags is []) or (id is '') or (not id.isdigit()):
			err("No, Just why  : "+str(id)+" : "+str(tags))
		dbInsertTags(conn,tags,id)
	elif options.insert is 'c':
		cmds=[]
		cmd='wget http://'
		while not (cmd == '' or cmd == 'EOC'):
			cmd=raw_input("Enter your command    : ")
			cmt=raw_input("Enter you comment     : ")
			if cmd not in ('','EOC'):
				cmds.append((cmd,cmt))
		dbInsertCmd(conn,cmds)
	elif options.insert is 'r':
		refs=[]
		ref='http://necurity.co.uk'
		id=raw_input("What CmdID are we adding refs to? : ")
		while ref != '':
			ref=raw_input("Enter a referance (blank for non) : ")
			if ref is not '':
				refs.append(ref)
		if (refs is []) or (id is '') or (not id.isdigit()):
			err("No, Just why  : "+str(id)+" : "+str(refs))
		dbInsertRefs(conn,refs,id)
	elif options.insert == "ta":
		cur = conn.cursor()
		ok("This tags everything without tags, mainly for DB init")
		ok("Enter blank line to commit changes")
		toTag=[]
		debug("S : SELECT CmdID,cmd,cmnt FROM tblcommand")
		cur.execute("SELECT CmdID,cmd,cmnt FROM tblcommand")
		cmds=cur.fetchall()
		debug("This Returned : "+str(cmds))
		for cmd in cmds:
			debug("S : SELECT tagid FROM tbltagmap WHERE cmdid = "+str(cmd[0]))
			cur.execute("SELECT tagid FROM tbltagmap WHERE cmdid = "+str(cmd[0]))
			TagCount=cur.fetchall()
			if (TagCount == []):
				toTag.append(cmd)
		debug ("Count : "+str(len(toTag))+"\nTagging : "+str(toTag))
		counter=len(toTag)
		for cmd in toTag:
			counter = counter-1
			tag='Easter Egg'
			tags=[]
			warn("Number left :"+str(counter))
			ok  ("Command ID : "+str(cmd[0]))
			ok  ("		Command    : "+str(cmd[1]))
			ok  ("		Comment    : "+str(cmd[2]))
			ok  ("v These are known tags")
			options.dump = 't'
			Dump(conn)
			print "==== ONE TAG A LINE ====\n"
			while tag != '':
				tag=raw_input("Enter a tag (blank for non) : ")
				if tag is not '':
					tags.append(tag)
				if (tags is []) or (cmd is ''):
					err("No, Just why  : "+str(cmd)+" : "+str(tags))
			dbInsertTags(conn,tags,cmd[0])

	else:
		err("RTFM : rtfh.py -h")

def Dump(conn):
	cur = conn.cursor()
	if (options.dump is 'a'):
		debug("Running Comand : SELECT * FROM Tblcommand")
		cur.execute("SELECT * FROM Tblcommand")
		rows=cur.fetchall()
		for cmd in rows:
			print cmd[1]
			print cmd[2]
			print 'EOC'
			tags=AsocTags(cur,str(cmd[0]))
			ltags = tags[-1].split("| ")
			for tag in ltags:
				if tag!='':
					print tag
			print 'EOT'
			refs=AsocRefs(cur,str(cmd[0]))
			lrefs = refs[-1].split("| ")
			for ref in lrefs:
				if ref!='':
					print ref
			print 'EOR'
		ok('Dumped all in update format. Why, you stealing things?')
	elif (options.dump is 'c'):
		debug("Running Comand : SELECT * FROM Tblcommand")
		cur.execute("SELECT * FROM Tblcommand")
		rows=cur.fetchall()
		for cmd in rows:
			print cmd[1]
			print cmd[2]
			print 'EOC'
	elif (options.dump is 't'):
		debug("Running Comand : SELECT tag FROM Tbltagcontent")
		cur.execute("SELECT Tag FROM Tbltagcontent")
		rows=cur.fetchall()
		for row in rows:
			sys.stdout.write(str(" | "+row[0])+" | ")
		sys.stdout.flush()
		print
	elif (options.dump is 'r'):
		debug("Running Comand : SELECT ref FROM Tblrefcontent")
		cur.execute("SELECT ref FROM Tblrefcontent")
		rows=cur.fetchall()
		for row in rows:
			print row[0]
		print 'EOR'
	else:
		err("RTFM: rtfm -h")

def PrintThing(ret_cmd):
	if (not options.printer):
		print "++++++++++++++++++++++++++++++"
		print "Command ID : "+str(ret_cmd[0])
		print "Command    : "+str(ret_cmd[1])+'\n'
		print "Comment    : "+str(ret_cmd[2])
		print "Tags       : "+str(ret_cmd[4])
		print "Date Added : "+str(ret_cmd[3])
		print "References\n__________\n"+str(ret_cmd[5])
		print "++++++++++++++++++++++++++++++\n"
	elif options.printer is 'p':
		print "++++++++++++++++++++++++++++++"
		print str(ret_cmd[1])+'\n'
		print str(ret_cmd[2])
		print "++++++++++++++++++++++++++++++\n"
	elif options.printer is 'w':
		print "="+str(options.cmd)+"="
	elif options.printer is 'P':
		table_data = [
			["Command ID ", str(ret_cmd[0])],
			["Command ", str(ret_cmd[1])],
			["Comment  ", str(ret_cmd[2])],
			["Tags  ", str(ret_cmd[4])],
			["Date added", str(ret_cmd[3])],
			["Referances",str(ret_cmd[5])]
			]
		table = AsciiTable(table_data)
		max_width = table.column_max_width(1)
		wrapped_string = '\n'.join(wrap(ret_cmd[1], max_width))+"\n"
		table.table_data[1][1] = wrapped_string
		print table.table
	else:
		err("Look im getting fed up of telling you how to do things")


def RefMapper(cur,refids):
	# XXX probabley shoud just change based on if ref or tag 
	if len(refids) == 1:
		debug("S : SELECT Ref from tblrefcontent where id ="+str(refids[0][0]))
		cur.execute("SELECT Ref from tblrefcontent where id = ?",refids[0])
		text=cur.fetchall()
		return(text[0][0])
	elif len(refids) > 1:
		# TODO : Yeh i know this is bad, but I will get round making it better at some point
		# AKA Yeh deal with it will probabley be here until the end of time
		sql="SELECT ref FROM tblrefcontent where id = -1 "
		for refid in refids:
			sql+=" OR id="+str(refid[0])
		debug("S : "+sql)
		cur.execute(sql)
		textlist=cur.fetchall()
		text=''
		for item in textlist:
			text+=item[0]+"\n"
		return(text)
	else:
		return("xXx ! No Refs for this ! xXx ")

def TagMapper(cur,tagids):
	if len(tagids) == 1:
		debug("S : SELECT tag from tbltagcontent where tagid ="+str(tagids[0][0]))
		cur.execute("SELECT tag from tbltagcontent where tagid = ?",tagids[0])
		text=cur.fetchall()
		return(text[0][0])
	elif len(tagids) > 1:
		# TODO : Yeh i know this is bad, but I will get round making it better at some point
		# AKA Yeh deal with it will probabley be here until the end of time
		sql="SELECT tag FROM tbltagcontent where tagid = -1 "
		for tagid in tagids:
			sql+=" OR tagid="+str(tagid[0])
		debug("S : "+sql)
		cur.execute(sql)
		textlist=cur.fetchall()
		text=''
		for item in textlist:
			text+="| "+item[0]+" "
		return(text)
	else:
		return("xXx ! No tags for this ! xXx ")

def SearchTagsnCmd(conn):
	cur = conn.cursor()
	debug("Running Comand : SELECT tagid FROM TblTagContent where Tags like '"+options.tag+"'")
	cur.execute("SELECT tagid FROM TblTagContent where Tag like '"+options.tag+"'")
	rows = cur.fetchall()
	debug("This Returned : "+str(rows))
	for row in rows:
		debug("Running : SELECT cmdid FROM TblTagMap where TagID = "+str(row[0])+" and cmd like")
		cur.execute("SELECT cmdid FROM TblTagMap where TagID = "+str(row[0]))
		ret_tags = cur.fetchall()
		debug("This Returned : "+str(ret_tags))
		for ret_tag in ret_tags:
			debug("Running : SELECT * FROM Tblcommand where CmdID = "+str(ret_tag[0])+" and cmd like '%"+str(options.cmd)+"%'")
			cur.execute("SELECT * FROM Tblcommand where cmdid = "+str(ret_tag[0])+" and cmd like '%"+str(options.cmd)+"%'")
			ret_cmds = cur.fetchall()
			debug("R : "+str(ret_cmds))
			for cmd in ret_cmds:
				cmd=AsocTags(cur,cmd)
				cmd=AsocRefs(cur,cmd)
				PrintThing(cmd)
def SearchTags(conn):
	cur = conn.cursor()
	debug("Running Comand : SELECT tagid FROM TblTagContent where Tags like '"+options.tag+"'")
	cur.execute("SELECT tagid FROM TblTagContent where Tag like '"+options.tag+"'")
	rows = cur.fetchall()
	debug("This Returned : "+str(rows))
	for row in rows:
		debug("Running : SELECT cmdid FROM TblTagMap where TagID = "+str(row[0]))
		cur.execute("SELECT cmdid FROM TblTagMap where TagID = "+str(row[0]))
		ret_tags = cur.fetchall()
		debug("This Returned : "+str(ret_tags))
		for ret_tag in ret_tags:
			debug("Running : SELECT * FROM Tblcommand where CmdID = "+str(ret_tag[0]))
			cur.execute("SELECT * FROM Tblcommand where cmdid = "+str(ret_tag[0]))
			ret_cmds = cur.fetchall()
			for cmd in ret_cmds:
				cmd=AsocTags(cur,cmd)
				cmd=AsocRefs(cur,cmd)
				PrintThing(cmd)

def SearchCommand(conn):
	cur = conn.cursor()
	debug("Running Comand : SELECT * FROM Tblcommand where cmd like '%"+options.cmd+"%'")
	cur.execute("SELECT * FROM Tblcommand where cmd like '%"+options.cmd+"%'")
	rows = cur.fetchall()
	debug("This Returned : "+str(rows))
	for cmd in rows:
		cmd=AsocTags(cur,cmd)
		cmd=AsocRefs(cur,cmd)
		PrintThing(cmd)

def AsocTags(cur,cmd):
	debug("S : SELECT TagID FROM tbltagmap WHERE cmdid = "+str(cmd[0]))
	cur.execute("SELECT TagID FROM tbltagmap WHERE cmdid = "+str(cmd[0]))
	RetTagIds=cur.fetchall()
	debug("This returned : "+str(RetTagIds)+" Len : "+str(len(RetTagIds)))
	Tags=TagMapper(cur,RetTagIds)
	l=list(cmd)
	l.append(Tags)
	cmd=tuple(l)
	return cmd

def AsocRefs(cur,cmd):
	debug("S : SELECT RefID FROM TblRefMap WHERE cmdid = "+str(cmd[0]))
	cur.execute("SELECT RefID FROM tblrefmap WHERE cmdid = "+str(cmd[0]))
	RetRefIds=cur.fetchall()
	debug("This returned : "+str(RetRefIds)+" Len : "+str(len(RetRefIds)))
	Tags=RefMapper(cur,RetRefIds)
	l=list(cmd)
	l.append(Tags)
	cmd=tuple(l)
	return cmd


#########################################################################
# XXX: Helpers
#########################################################################

def debug(msg, override=False):
	if options.debug or override:
		print ANSI["purple"] + ANSI["bold"] + "[DEBUG]: " + ANSI["reset"] + msg

def ok(msg):
	print ANSI["green"] + ANSI["bold"] + "[OK]: " + ANSI["reset"] + msg

def warn(msg):
	msg =  ANSI["yellow"] + ANSI["bold"] + "[WARNING]: " + \
		ANSI["reset"] + msg + "\n"

	sys.stderr.write(msg)

def err(msg, level="generic"):
	if level.lower() not in EXIT_CODES:
		level = "generic"

	msg =  ANSI["red"] + ANSI["bold"] + "[ERROR]: " + \
		ANSI["reset"] + msg + "\n"

	sys.stderr.write(msg)
	sys.exit(EXIT_CODES[level])


#########################################################################
# XXX: Initialisation
#########################################################################
try:
	from terminaltables import AsciiTable
	from textwrap import wrap
except:
	warn("Unable to have pretty output, Please 'pip install terminaltables' or remove these lines :)")

if __name__ == "__main__":
	parser = optparse.OptionParser(
		usage="Usage: %prog [OPTIONS]",
		version="%s: v%s (%s)" % (__prog__, __version__, ', '.join(__authors__)),
		description="For when you just cant remember the syntax, you should just RTFM",
		epilog="Example:rtfm.py -t windows rtfm.py -d tags",
	)

	parser.add_option("-t", "--tag", action="store", dest="tag",
		help="Specify one or more tags to look for (a,b,c)")

	parser.add_option("-c", "--cmd", action="store", dest="cmd",
		help="Specify a command to search (ls)")

	parser.add_option('-R', '--ref', action='store_true', dest="ref",
		help="Show the referances for cmd ID (1)")

	parser.add_option('-p', '--print', action='store', dest="printer",
		help="Print Types : P(retty) p(astable) w(iki) h(tml)")

	parser.add_option('-i', '--insert', action='store', dest="insert",
		help="Insert c(ommand) | t(ags) r(eferances)")

	parser.add_option('-D', '--dump', action='store', dest="dump",
		help="Just Dump infomration about t(ags)|c(commands)|r(eferances)a(ll)")

	parser.add_option('-d', '--debug', action='store_true', dest="debug",
		help='Display verbose processing details (default: False)')

	parser.add_option('-u', '--update', action='store_true', dest="update",
		help='Check for updates (default: false)')

	parser.add_option('-v', action='version',
		help="Shows the current version number and the current DB hash and exits")


	(options, args) = parser.parse_args()

	try:
		debug("Options Set: "+str(options))
		run()
	except KeyboardInterrupt:
		print "\n\nCancelled."
		sys.exit(0)
