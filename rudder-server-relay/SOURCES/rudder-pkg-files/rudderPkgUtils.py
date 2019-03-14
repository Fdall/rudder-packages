import os, logging, sys, re, hashlib, configparser, requests, json
import distutils.spawn
from pprint import pprint
from pkg_resources import parse_version
from subprocess import Popen, PIPE
from clint.textui import progress

# See global variables at the end of the file

"""
    Start two different loggers:
      -one for the output           => stdoutHandler
      -another one for the log file => fileHandler
    They have the same root, so logging is common to both handler,
    but they will each log what they should based on their log level.
"""
def startLogger(logLevel):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # stdout logger
    stdoutHandler = logging.StreamHandler(sys.stdout)
    stdoutFormatter = logging.Formatter('%(message)s')
    stdoutHandler.setFormatter(stdoutFormatter)
    if logLevel == 'INFO':
        stdoutHandler.setLevel(logging.INFO)
    elif logLevel == 'DEBUG':
        stdoutHandler.setLevel(logging.DEBUG)
    else:
        fail("unknow loglevel %s"%(logLevel))

    # log file logger
    fileHandler = logging.FileHandler(filename=LOG_PATH , mode='w')
    fileHandler.setLevel(logging.DEBUG)
    fileFormatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fileHandler.setFormatter(fileFormatter)

    root.addHandler(stdoutHandler)
    root.addHandler(fileHandler)

"""

    Run a command in a shell like a script would do
    And inform the user of its execution.
"""
def shell(command, comment=None, keep_output=False, fail_exit=True, keep_error=False):
  if comment is not None:
    logging.info(comment)
    logging.info(" $ " + command)
  if keep_output or keep_error:
    if keep_output:
      keep_out = PIPE
    else:
      keep_out = None
    if keep_error:
      keep_err = PIPE
    else:
      keep_err = None
    process = Popen(command, stdout=keep_out, stderr=keep_err, shell=True, universal_newlines=True)
    output, error = process.communicate()
    retcode = process.poll()
  else: # keep tty management and thus colors
    process = Popen(command, shell=True)
    retcode = process.wait()
    output = None
    error = None
  if fail_exit and retcode != 0:
    logging.error("execution of '%s' failed"%(command))
    logging.error(error)
    fail(output, retcode)
  return (retcode, output, error)

def fail(message, code=1):
    logging.error(message)
    exit(code)

def sha512(fname):
    hash_sha512 = hashlib.sha512()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha512.update(chunk)
    return hash_sha512.hexdigest()

def createPath(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            fail("Could not create dir %s"%(path))

"""
   From a complete url, try to download a file. The destination path will be determined by the complete url
   after removing the prefix designing the repo url defined in the conf file.
   Ex: completeUrl = http://download.rudder.io/plugins/./5.0/windows/release/SHA512SUMS
           repoUrl = http://download.rudder.io/plugins
           localCache = /tmp/rpkg
        => fileDst = /tmp/rpkg/./5.0/windows/release/SHA512SUMS
"""
def download(completeUrl, dst=""):
    if dst == "":
        fileDst = FOLDER_PATH + "/" + completeUrl.replace(URL + "/", '')
    else:
        fileDst = dst
    fileDir = os.path.dirname(fileDst)
    createPath(fileDir)
    r = requests.get(completeUrl, auth=(USERNAME, PASSWORD), stream=True)
    with open(fileDst, 'wb') as f:
       total_length = int(r.headers.get('content-length'))
       if r.status_code == 200:
           # Add progress bar
           for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1): 
               if chunk:
                   f.write(chunk)
                   f.flush()
       elif r.status_code == 401:
           fail("Received a HTTP 401 Unauthorized error when trying to get %s. Please check your credentials in %s"%(completeUrl, CONFIG_PATH))
       elif r.status_code > 400:
           fail("Received a HTTP %s error when trying to get %s"%(r.status_code, completeUrl))
    return fileDst

"""
   Verify Hash
"""
def verifyHash(targetPath, shaSumPath):
    fileHash = []
    (folder, leaf) = os.path.split(targetPath)
    lines = [line.rstrip('\n') for line in open(shaSumPath)]
    pattern = re.compile(r'(?P<hash>[a-zA-Z0-9]+)[\s]+%s'%(leaf))
    logging.info("verifying file hash")
    for line in lines:
        match = pattern.search(line)
        if match:
            fileHash.append(match.group('hash'))
    if len(fileHash) != 1:
        logging.warning('Multiple hash found matching the package, this should not happend')
    if sha512(targetPath) in fileHash:
        logging.info("=> OK!\n")
        return True
    utils.fail("hash could not be verified")


"""
   From a complete url, try to download a file. The destination path will be determined by the complete url
   after removing the prefix designing the repo url defined in the conf file.
   Ex: completeUrl = http://download.rudder.io/plugins/./5.0/windows/release/SHA512SUMS
           repoUrl = http://download.rudder.io/plugins
           localCache = /tmp/rpkg
        => fileDst = /tmp/rpkg/./5.0/windows/release/SHA512SUMS

   If the verification or the download fails, it will exit with an error, otherwise, return the path
   of the local rpkg path verified and downloaded.
"""
def download_and_verify(completeUrl, dst=""):
    global GPG_HOME
    # donwload the target file
    logging.info("downloading rpkg file  %s"%(completeUrl))
    targetPath = download(completeUrl, dst)
    # download the attached SHASUM and SHASUM.asc
    (baseUrl, leaf) = os.path.split(completeUrl)
    logging.info("downloading shasum file  %s"%(baseUrl + "/SHA512SUMS"))
    shaSumPath = download(baseUrl + "/SHA512SUMS", dst)
    logging.info("downloading shasum sign file  %s"%(baseUrl + "/SHA512SUMS.asc"))
    signPath = download(baseUrl + "/SHA512SUMS.asc", dst)
    # verify authenticity
    gpgCommand = "/usr/bin/gpg --homedir " + GPG_HOME + " --verify " + signPath + " " + shaSumPath
    logging.debug("Executing %s"%(gpgCommand))
    logging.info("verifying shasum file signature %s"%(gpgCommand))
    shell(gpgCommand, keep_output=False, fail_exit=True, keep_error=False)
    logging.info("=> OK!\n")
    # verify hash
    if verifyHash(targetPath, shaSumPath):
        return targetPath
    fail("Hash verification of %s failed"%(targetPath))
    

"""Download the .rpkg file matching the given rpkg Object and verify its authenticity"""
def downloadByRpkg(rpkg):
    return download_and_verify(URL + "/" + rpkg.path)

def package_check(metadata):
  if 'type' not in metadata or metadata['type'] != 'plugin':
    fail("Package type not supported")
  # sanity checks
  if 'name' not in metadata:
    fail("Package name undefined")
  name = metadata['name']
  if 'version' not in metadata:
    fail("Package version undefined")
  # incompatibility check
  if metadata['type'] == 'plugin':
    if not check_plugin_compatibility(metadata):
      fail("Package incompatble with this Rudder version, please use a more recent one")
  # do not compare with exiting version to allow people to reinstall or downgrade
  return name in DB['plugins']


def check_plugin_compatibility(metadata):
  # check that the given version is compatible with Rudder one
  match = re.match(r'(\d+\.\d+)-(\d+)\.(\d+)', metadata['version'])
  if not match:
    fail("Invalid package version " + metadata['version'])
  rudder_version = match.group(1)
  major_version = match.group(2)
  minor_version = match.group(3)
  if rudder_version != RUDDER_VERSION:
    return False

  # check specific constraints
  full_name = metadata['name'] + '-' + metadata['version']
  if full_name in COMPATIBILITY_DB['incompatibles']:
    return False
  return True

"""Add the rudder key to a custom home for trusted gpg keys"""
def getRudderKey():
    logging.debug("check if rudder gpg key is already trusted")
    checkKeyCommand = "/usr/bin/gpg --homedir " + GPG_HOME + " --fingerprint"
    output = shell(checkKeyCommand, keep_output=True, fail_exit=False, keep_error=False)[1]
    if output.find(GPG_RUDDER_KEY_FINGERPRINT) == -1:
        logging.debug("rudder gpg key was not found, adding it from %s"%(GPG_RUDDER_KEY))
        addKeyCommand = "/usr/bin/gpg --homedir " + GPG_HOME + " --import " + GPG_RUDDER_KEY
        # Could not find why, but at creation, we need to run it 2 times to work properly
        shell(addKeyCommand, keep_output=True, fail_exit=True, keep_error=False)
        logging.debug("executing %s"%(addKeyCommand))
    logging.debug("=> OK!")

# Indexing methods
def db_load():
  """ Load the index file into a global variable """
  global DB, COMPATIBILITY_DB
  if os.path.isfile(DB_FILE):
    with open(DB_FILE) as fd:
      DB = json.load(fd)
  if os.path.isfile(COMPATIBILITY_FILE):
    with open(COMPATIBILITY_FILE) as fd:
      COMPATIBILITY_DB = json.load(fd)

def db_save():
  """ Save the index into a file """
  with open(DB_FILE, 'w') as fd:
    json.dump(DB, fd)


def rpkg_metadata(package_file):
  (_, output, _) = shell("ar p '" + package_file + "' metadata", keep_output=True)
  return json.loads(output)

def install_dependencies(metadata):
  # not supported yet
  has_depends = False
  depends_printed = False
  if "depends" in metadata:
    for system in metadata["depends"]:
      if system == "binary":
        for executable in metadata["depends"][system]:
          if distutils.spawn.find_executable(executable) is None:
            logging.warning("The binary " + executable + " was not found on the system, you must install it before installing " + metadata['name'])
            return False
      else:
        has_depends = True
        if not depends_printed:
          logging.info("This package depends on the following")
          depends_printed = True
        logging.info("  on " + system + " : " + ", ".join(metadata["depends"][system]))
    if has_depends:
      logging.info("It is up to you to make sure those dependencies are installed")
  return True


def extract_scripts(metadata,package_file):
  package_dir = DB_DIRECTORY + "/" + metadata["name"]
  shell("mkdir -p " + package_dir + "; ar p '" + package_file + "' scripts.txz | tar xJ --no-same-owner -C " + package_dir)
  return package_dir


def run_script(name, script_dir, exist):
  script = script_dir + "/" + name 
  if os.path.isfile(script):
    if exist is None:
      param = ""
    elif exist:
      param = "upgrade"
    else:
      param = "install"
    shell(script + " " + param)


def jar_status(name, enable):
  global jetty_needs_restart
  text = open(PLUGINS_CONTEXT_XML).read()
  def repl(match):
    enabled = [x for x in match.group(1).split(',') if x != name and x != '']
    pprint(enabled)
    if enable:
      enabled.append(name)
    plugins = ','.join(enabled)
    return '<Set name="extraClasspath">' + plugins + '</Set>'
  text = re.sub(r'<Set name="extraClasspath">(.*?)</Set>', repl, text)
  open(PLUGINS_CONTEXT_XML, "w").write(text)
  jetty_needs_restart = True


def remove_files(metadata):
  for filename in reversed(metadata['files']):
    # ignore already removed files
    if not os.path.exists(filename):
      logging.info("Skipping removal of " + filename + " as it does not exist")
      continue

    # remove old files
    if filename.endswith('/'):
      try:
        os.rmdir(filename)
      except OSError:
        pass
    else:
      os.remove(filename)


def install(metadata, package_file, exist):
  if exist:
    remove_files(DB['plugins'][metadata['name']])
  # add new files
  files = []
  for tarfile in metadata['content']:
    dest = metadata['content'][tarfile]
    (_, file_list, _) = shell("mkdir -p " + dest + "; ar p '" + package_file + "' " + tarfile + " | tar xJv --no-same-owner -C " + dest, keep_output=True)
    files.append(dest+'/')
    files.extend([ dest + '/' + x for x in file_list.split("\n") if x != ''])

  metadata['files'] = files
  # update db
  DB['plugins'][metadata['name']] = metadata
  db_save()

def readConf():
    # Repos specific variables
    global REPO, URL, USERNAME, PASSWORD
    logging.debug('Reading conf file %s'%(CONFIG_PATH))
    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)
        REPO = config.sections()[0]
        URL = config[REPO]['url']
        USERNAME = config[REPO]['username']
        PASSWORD = config[REPO]['password']
        createPath(FOLDER_PATH)
        createPath(GPG_HOME)
    except Exception as e:
        print("Could not read the conf file %s"%(CONFIG_PATH))
        exit(1)

def list_plugin_name():
    global INDEX_PATH
    try:
        pluginName = {}
        with open(INDEX_PATH) as f:
            data = json.load(f)
        for metadata in data:
            if metadata['name'] not in pluginName.keys():
                if "description" in metadata:
                    description = metadata['description']
                    if len(description) >= 80:
                        description = description[0:76] + "..."
                    pluginName[metadata['name']] = (metadata['name'].replace("rudder-plugin-", ""), description)
                else:
                    pluginName[metadata['name']] = (metadata['name'].replace("rudder-plugin-", ""), "")
        return pluginName
    except:
        fail("Could not read the index file %s"%(INDEX_PATH))

############# Variables ############# 
""" Defining global variables."""

LOG_PATH = "/var/log/rudder/rudder-pkg.log"
CONFIG_PATH = "/opt/rudder/etc/rudder-pkg.conf"
FOLDER_PATH = "/var/rudder/tmp/plugins"
INDEX_PATH = FOLDER_PATH + "/rpkg.index"
GPG_HOME = "/tmp/toto"
GPG_RUDDER_KEY = "/var/rudder/rudder_apt_key.pub"
GPG_RUDDER_KEY_FINGERPRINT = "7C16 9817 7904 212D D58C  B4D1 9322 C330 474A 19E8"


p = Popen("rudder agent version", shell=True, stdout=PIPE)
line = p.communicate()[0]
m = re.match(r'Rudder agent (\d+\.\d+)\..*', line.decode('utf-8'))
if m:
  RUDDER_VERSION=m.group(1)
else:
  print("Cannot retrieve major version, ABORTING !")
  exit(1)

# Local install specific variables
DB = { "plugins": { } }
DB_DIRECTORY = '/var/rudder/packages'
# Contains the installed package database
DB_FILE = DB_DIRECTORY + '/index.json'
# Contains known incompatible plugins (installed by the relay package)
# this is a simple list with names od the form "plugin_name-version"
COMPATIBILITY_DB = { "incompatibles": [] }
COMPATIBILITY_FILE = DB_DIRECTORY + '/compatible.json'
# Plugins specific resources
PLUGINS_CONTEXT_XML = "/opt/rudder/share/webapps/rudder.xml"
jetty_needs_restart = False
