#!/usr/bin/env python3

# ~/.ssh/authorized_keys
# command="..../bin/ssh-wrapper.py",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty  ssh-rsa ....

import os, sys, re, fcntl, subprocess

def git_upload_pack(path):
	print('git-upload-pack PATH: ' + path, file=sys.stderr)
	localpath = None
	url = None
	m = re.match('^/(http|https)/(.*)$', path)
	if m:
		relpath = '/' + m.group(1) + '/' + m.group(2)
		url = m.group(1) + '://'  + m.group(2)
	else:
		print('git-upload-pack: Unknown protocol.', file=sys.stderr)
		return 1

	relpath = os.path.normpath(relpath)
	relpath = os.path.relpath(relpath, '/')
	localpath = os.path.abspath(os.path.join('mirror', relpath))

	lockfile = os.path.join(os.path.dirname(localpath), os.path.basename(localpath) + '.lock')

	print('git-upload-pack localpath ' + localpath, file=sys.stderr)
	print('git-upload-pack url ' + url, file=sys.stderr)
	print('git-upload-pack lockfile ' + lockfile, file=sys.stderr)

	if os.path.exists(localpath) and not os.path.isdir(localpath):
		print("git-upload-path not directory: localpath", file=sys.stderr)
		return 2

	if not os.path.exists(localpath):
		os.makedirs(localpath)
	
	lockfd = open(lockfile, 'w+')
	locked_ex = False
	locked_sh = False

	try:
		fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
		print("EX lock maked", file=sys.stderr)
		locked_ex = True
	except IOError as e:
		#if e.errno != errno.EAGAIN:
		#	raise
		pass

	while not locked_ex and True:
		try:
			fcntl.flock(lockfd, fcntl.LOCK_SH | fcntl.LOCK_NB)
			print("SH lock maked", file=sys.stderr)
			locked_sh = True
			break
		except IOError as e:
			if e.errno != errno.EAGAIN:
				pass
			else:
				time.sleep(0.3)
	

	if locked_ex:
		new_repo = True
		if os.path.exists(os.path.join(localpath, 'config')):
			new_repo = False

		if new_repo:
			print("Clone origin repo.", file=sys.stderr)
			sys.stderr.flush()
			ret = subprocess.call(['git', 'clone', '--bare', '--', url, localpath], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
			if ret != 0:
				return 3
		else:
			print("Fetch new data from origin repo.", file=sys.stderr)
			sys.stderr.flush()
			os.chdir(localpath)
			ret = subprocess.call(['git', 'fetch', url], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
			if ret != 0:
				return 4

	if locked_ex or locked_sh:
		print("git serve data.", file=sys.stderr)
		sys.stderr.flush()
		ret = subprocess.call(['git-upload-pack', localpath], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
		return ret

	return 2

ssh_origin_command = None

if 'SSH_ORIGINAL_COMMAND' in os.environ:
	ssh_origin_command = os.environ['SSH_ORIGINAL_COMMAND']
else:
	print('Missing SSH_ORIGINAL_COMMAND', file=sys.stderr)
	sys.exit(1)


# git-upload-pack '/mirror/https/github.com/aur-archive/proxychains-git.git'
match = re.match('^git-upload-pack\s+\'(.*)\'$', ssh_origin_command)
if match:
	ret = git_upload_pack(match.group(1))
	sys.exit(ret)

print('Unknwon command ' + ssh_origin_command, file=sys.stderr)

sys.exit(0)
