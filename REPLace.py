#!/usr/bin/python3

# -----------------------
# things to do
# -----------------------

# make an option to run different versions of mpy-cross

# pipx install mpy-cross==1.18
# can be run normally as mpy-cross
# pipx install --suffix=_1.17 mpy-cross==1.17
# can be also run from command line as mpy-cross_1.17

# -----------------------
# general imports
# -----------------------

import os
import sys
import time
import shutil
import argparse
import json
import serial
import traceback

try:
    import mpy_cross
except:
    mpy_cross = None
    print()
    print('ERROR: mpy-cross NOT installed. No pre-compile.')
    print('IMPORTANT: Install mpy-cross.')
    print('USE THIS: python3 -m pip install mpy-cross')
    print()

# -----------------------
# default variables
# -----------------------

version = 2.0
port = None
port_list = ['/dev/ttyUSB0', "/dev/tty.SLAB_USBtoUART", "COM3", "COM1"]
smash = 3
smash_keep = False
smash_all = False
verbose = False
use_mpy = True
make_mpy = True
dry_run = False
file_root = os.getcwd()
file_lists = ['REPLace.lst']
file_configs = ['includes.json']
load_all = False
includes = []
excludes = [

    # files
    'REPLace.py',
    'MPY6.py',
    'notes.txt',
    'requirements.txt',
    'includes.json',
    'template_networks.csv',
    'template_config.json',
    'README.md',
    '*.bin',

    # directories
    '__pycache__',
    '__builtins__',
    'archive',
    'hidden',
    'install',
    'thumbs',
    'video',
    'examples',
    'example',

    ]

# -----------------------
# command line variables
# -----------------------

epilog = f'''
examples:
  ./REPLace.py works the same as python3 REPLace.py in Linux
  ./REPLace.py -a --> load all files but exceptions
  ./REPLace.py -l --> load files in default list {file_lists}
  ./REPLace.py -c --> load files in default config {file_configs}
  ./REPLace.py -i file1.py file2.py --> load (i.e. include) just these

notes:
  you can use all the flags together, they logically cancel each other
  you must use -a, -i, -l, or -c to load any files
  if you use -a then -i, -l, -c are ignored
  use -l or -c by itself to use the default list or config
  if a -l or -c file is given, the default is ignored
  if -i file.py is used, -l and -c are not

list files:
  put one include file per line
  put one exclude file per line
  exclude files are preceded by "exclude"
  for example "exclude junk.py"
  if a line starts with "end " the read stops
  use "end " to hide extra lines

config files:
  config files are JSON
  the file must contain a single object {{...}}
  the includes and excludes are in lists in the object
  {{"includes":["file","file"],
   "excludes":["file","file"]}}
_
'''.strip()

parser = argparse.ArgumentParser(description='Load files to an ESP32 via the REPL',
                                 formatter_class=argparse.RawTextHelpFormatter,
                                 epilog=epilog)

parser.add_argument('--version', action='version',version=f'REPLace.py {version}')
parser.add_argument('-p', dest='port', help='define the REPL port name')
parser.add_argument('-r', dest='root', help='define ROOT dir for files')

parser.add_argument('-s', choices=['0', '1', '2', '3'], help='set the SMASH level')
parser.add_argument('-n', action='store_true', help='flag: smash NON-python files')
parser.add_argument('-k', action='store_true', help='flag: KEEP smashed files')
parser.add_argument('-v', action='store_true', help='flag: verbose, show loaded bytes')

parser.add_argument('-a', action='store_true', help='flag: load ALL non-exclude files')
parser.add_argument('-l', nargs='*', help='define LISTING files')
parser.add_argument('-c', nargs='*', help='define CONFIG files')

parser.add_argument('-i', nargs='*', help='filenames to INCLUDE in load')
parser.add_argument('-e', nargs='*', help='filenames to EXCLUDE from load')
parser.add_argument('-x', nargs='*', help='filenames to XCLUDE from default excludes')


parser.add_argument('--xmpy', action='store_true', help="flag: don't use .mpy files")
parser.add_argument('--zmpy', action='store_true', help="flag: don't make/remake .mpy files")
parser.add_argument('--dryrun', action='store_true', help="flag: don't load files")

args = parser.parse_args()

# -----------------------
# merge variables
# -----------------------

if args.port:
    port = args.port

if args.root:
    file_root = os.path.abspath(args.root)

if args.s:
    smash = int(args.s)

if args.n:
    smash_all = True

if args.k:
    smash_keep = True

if args.a:
    load_all = True

if args.v:
    verbose = True

if args.xmpy:
    use_mpy = False

if args.zmpy:
    make_mpy = False

if args.dryrun:
    dry_run = True

# file lists
if load_all:
    file_lists = []
elif args.l == None:
    file_lists = []
elif args.l:
    file_lists = args.l
else:
    pass  # use default

# config lists
if load_all:
    file_configs = []
elif args.c == None:
    file_configs = []
elif args.c:
    file_configs = args.c
else:
    pass  # use default

# includes
if args.i:
    includes = args.i

# excludes
if args.e:
    for f in args.e:
        if f not in excludes:
            excludes.append(f)
if args.x:
    for f in args.x:
        while f in excludes:
            i = excludes.index(f)
            excludes.pop(i)

includes = set(includes)
excludes = set(excludes)

# -----------------------
# print basics
# -----------------------

div = '-'*64

print()
print(f'REPLace.py {version}')

print(div)
print('PORT:', port)
print('SMASH:', smash)
print('SMASH_ALL:', smash_all)
print('SMASH_KEEP:', smash_keep)
print('LOAD_ALL:', load_all)
print('FILE_ROOT:', file_root)
print('FILE_LISTS:', file_lists)
print('FILE_CONFIGS:', file_configs)

# -----------------------
# read lists
# -----------------------

if file_lists:
    print(div)
    for file in file_lists:
        print(f'READ LIST: {file}', end=' ')
        if os.path.isfile(file):
            path = os.path.abspath(file)
        elif os.path.isfile(os.path.join(file_root, file)):
            path = os.path.join(file_root, file)
        else:
            print('NOT FOUND')
            continue
        ic, ec = 0, 0
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line and line[0] != '#':
                    line = line.split()
                    if line[0].lower() == 'end':
                        break
                    elif line[0].lower() == 'exclude':
                        if len(line) >= 2:
                            excludes.add(os.path.basename(line[1]))
                            ec += 1
                    elif line[0].lower() == 'include':
                        if len(line) >= 2:
                            includes.add(os.path.basename(line[1]))
                            ic += 1
                    else:
                        includes.add(os.path.basename(line[0]))
                        ic += 1
            f.close()
        print(f'({ic} includes, {ec} excludes)')

# -----------------------
# read configs
# -----------------------

if file_configs:
    print(div)
    for file in file_configs:
        print(f'READ CONFIG: {file}', end=' ')
        if os.path.isfile(file):
            path = os.path.abspath(file)
        elif os.path.isfile(os.path.join(file_root, file)):
            path = os.path.join(file_root, file)
        else:
            print('NOT FOUND')
            continue
        ic, ec = 0, 0
        try:
            with open(file) as f:
                data = json.load(f)
                f.close()
        except:
            print('BAD JSON')
            continue
        if data.get('load_all', False):
            load_all = True
        for filename in data.get('includes', []):
            includes.add(os.path.basename(filename))
            ic += 1
        for filename in data.get('excludes', []):
            excludes.add(os.path.basename(filename))
            ec += 1
            f.close()
        print(f'({ic} includes, {ec} excludes)')

# -----------------------
# print excludes
# -----------------------

if excludes:
    excludes = list(excludes)
    excludes.sort()
    print(div)
    for f in excludes:
        print('EXCLUDE:', f)

# -----------------------
# iter over root
# -----------------------

if load_all:
    includes = set()

loads = []
alldirs = set()

if load_all or includes:
    for root,dirs,files in os.walk(file_root):

        # drop bad dirs
        for d in dirs[:]:
            for x in excludes:
                if d == x:
                    dirs.remove(d)
                elif x.startswith('*') and d.endswith(x[1:]):
                    dirs.remove(d)
                elif x.endswith('*') and d.startswith(x[:-1]):
                    dirs.remove(d)

        # save good files
        files_saved_from_this_dir = set()
        for file in files:

            keepit = False

            # no smash files
            if root == file_root and file.startswith('smash_'):
                continue

            # no specific excludes
            if excludes:
                excluded = False
                for x in excludes:
                    if file == x:
                        excluded = True
                        break
                    elif x.startswith('*') and file.endswith(x[1:]):
                        excluded = True
                        break
                    elif x.endswith('*') and file.startswith(x[:-1]):
                        excluded = True
                        break
                if excluded:
                    continue

            # all
            if load_all:
                keepit = True

            # specific include
            elif file in includes:
                keepit = True

            # save
            if keepit:

                # conditional select of mpy
                name,ext = os.path.splitext(file)
                
                # mpy file
                if ext.lower() == '.mpy':
                    if not use_mpy:
                        file = None

                # python file
                elif ext.lower() == '.py':

                    # don't use mpy
                    if not use_mpy:
                        pass

                    # don't make mpy (but use what you have)
                    elif not make_mpy:
                        if os.path.isfile(os.path.join(root,name+'.mpy')):
                            file = name+'.mpy'

                    # can't make mpy (so use what you have)
                    elif not mpy_cross:
                        if os.path.isfile(os.path.join(root,name+'.mpy')):
                            file = name+'.mpy'

                    # mpy already in list
                    elif name+'.mpy' in files_saved_from_this_dir:
                        file = None

                # make/save paths
                if file and file not in files_saved_from_this_dir:
                    path1 = os.path.join(root,file)
                    path2 = os.path.normpath(path1.replace(file_root,'').strip(os.sep))
                    loads.append((path2,path1))
                    alldirs.add(os.path.dirname(path2))
                    files_saved_from_this_dir.add(file)

alldirs = list(alldirs)
alldirs.sort()

# -----------------------
# print loads (includes)
# -----------------------

if loads:
    loads.sort()
    print(div)
    for p1,p2 in loads:
        print('INCLUDE:',p1)

# -----------------------
# dry run
# -----------------------

if dry_run:

    print(div)
    print(f'DRY RUN: 0 files loaded')
    print()
    exit(0)

# -----------------------
# serial
# -----------------------

rbuffer = ''

def recv():

    # clear recv into rbuffer

    global rbuffer
    while 1:
        data = connection.read(1024)
        if not data:
            break
        else:
            rbuffer += data.decode(encoding='utf-8', errors='?')


def send(line='',show=False,validate=None):

    global rbuffer

    connection.write([ord(x) for x in line+'\r'])
    time.sleep(0.1)
    recv()

    if validate and not rbuffer.rstrip().endswith(validate.strip()):
        print('VALIDATE:',[validate.strip()])
        print('R_BUFFER:',[rbuffer.rstrip()[-64:]])
        raise IOError('RECV buffer FAILED validation.')

    if show:
        print('BLOCK:', [' '.join(rbuffer.split(' '))])

    rbuffer = ''

if verbose:
    print(div)

baudrate = 115200
timeout = 0.1

if port:
    connection = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
elif port_list:
    connection = None
    for p in port_list:
        try:
            connection = serial.Serial(port=p, baudrate=baudrate, timeout=timeout)
            break
        except:
            print(f'PORT UNAVAILABLE: {p}')
if connection == None:
    raise Exception('SERIAL POER ERROR: Use -p PORT to specify a serial port.')

connection.flush()
connection.write([3])  # clear = ctrl-c = 0x03
time.sleep(0.2)
connection.write([3])  # clear = ctrl-c = 0x03
time.sleep(0.2)
connection.write([3])  # clear = ctrl-c = 0x03
time.sleep(0.2)
send(show=verbose)

send('import os', show=verbose)
send('os.chdir("/")', show=verbose)

# -----------------------
# load files
# -----------------------

fc = 0
fileblocksize = 1024

if loads:

    # make dirs
    if alldirs:
        print(div)
        dirsmade = set()
        for d in alldirs:
            subdirs = [x.strip() for x in d.split(os.sep) if x.strip()]
            if subdirs:
                for x in range(len(subdirs)):
                    d2 = os.path.join(*subdirs[:x+1])
                    if d2 in dirsmade:
                        continue
                    else:
                        print('MAKE DIR:',d2)
                        dirname, basename = os.path.split(d2)
                        if dirname:
                            send(f"if '{basename}' not in os.listdir('{dirname}'): os.mkdir('{dirname}/{basename}')\r\n",show=verbose)
                            send(f"'{basename}' in os.listdir('{dirname}')",show=verbose,validate='True\r\n>>>')
                        else:
                            send(f"if '{basename}' not in os.listdir(): os.mkdir('{basename}')\r\n",show=verbose)
                            send(f"'{basename}' in os.listdir()",show=verbose,validate='True\r\n>>>')
                        send()
                        dirsmade.add(d2)

    # make files
    for p1, p2 in loads:

        print(div)
        print('LOADING:', p1)

        # make temp file
        temp = 'smash_'+os.path.basename(p1)

        # ext
        ext = os.path.splitext(p2)[1].lower()

        # mpy-cross
        if ext == '.py' and use_mpy and make_mpy and mpy_cross and os.path.basename(p2) not in ('boot.py','main.py'):
            print('Cross Compile:',os.path.basename(p2),end=' ')
            # rename files to .mpy
            temp = temp.replace('.py','.mpy')
            p1 = p1.replace('.py','.mpy')
            if os.path.isfile(temp):
                os.remove(temp)
            mpy_cross.run('-o',temp,p2).wait() # doesn't raise errors, use file existence
            print('done')
            if not os.path.isfile(temp):
                print('ERROR:',os.path.basename(p2),'does not compile.')
                print()
                print('COMPILE ERROR! REPLace.py STOPPED.')
                print()
                break

        # old smash
        elif smash and ext != '.mpy' and (smash_all or ext == '.py'):
            with open(p2) as infile:
                with open(temp,mode='w',newline='\n') as outfile:
                    for line in infile:
                        line2 = line.strip() # this will remove \r
                        if not line2:
                            pass
                        elif line2 == '# end':
                            break
                        elif line2.startswith('#') and smash >= 2:
                            pass
                        elif '#' in line2 and smash >= 3:
                            outfile.write(line.rstrip().rsplit('#', 1)[0]+'\n')
                        else:
                            outfile.write(line.rstrip()+'\n')
                    outfile.close()
                infile.close()

        # no smash
        else:
            shutil.copyfile(p2,temp)

        # send temp file
        send_error = False
        for x in range(3):
            try:
                bc = 0
                send(f"outfile = open('{p1}',mode='wb')", show=verbose)
                infile = open(temp, mode='rb')
                while 1:
                    data = infile.read(fileblocksize)
                    if not data:
                        break
                    bc += len(data)
                    send(f"outfile.write({data})",show=verbose,validate=f'{len(data)}\r\n>>>')
                send("outfile.close()", show=verbose)
                if send_error:
                    print('RELOAD OKAY')
                print(f'LOADED: {bc} bytes OKAY')
                send_error = False
                break
            except Exception as e:
                send("outfile.close()",show=False)
                print(traceback.format_exc())
                if x <= 1:
                    print('RELOADING')
                send_error = True
                connection.write([3]) # clear = ctrl-c = 0x03
                time.sleep(0.2)
                connection.write([3]) # clear = ctrl-c = 0x03
                time.sleep(0.2)
                connection.write([3]) # clear = ctrl-c = 0x03
                time.sleep(0.2)             
        if send_error:
            raise Exception('FILE LOAD ERROR:',os.path.basename(p2))

        # remove temp file
        if not smash_keep:
            if os.path.isfile(temp):
                os.remove(temp)

        # count
        fc += 1

        # try a pause
        #time.sleep(0.1)

# -----------------------
# serial
# -----------------------

if verbose:
    print(div)

connection.write([3])  # clear = ctrl-c = 0x03
time.sleep(0.2)
connection.write([3])  # clear = ctrl-c = 0x03
time.sleep(0.2)
connection.write([3])  # clear = ctrl-c = 0x03
time.sleep(0.2)
send(show=verbose)
connection.close()

# -----------------------
# print done
# -----------------------

print(div)
print(f'DONE: {fc} files loaded')
print()

# -----------------------
# end
# -----------------------
