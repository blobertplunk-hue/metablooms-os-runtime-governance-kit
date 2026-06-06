# COMPOSITE LOAD SUSTAINED 10s PROBE (STAGGERED)


## Method
- Allocate memory, open FDs, spawn processes staggered over ~1s
- Sustain for ~10 seconds
- Observe completion vs interruption


## mem_512_proc_60_fd_512_dur_10_staggered

- returncode: 1

- wall_elapsed_seconds: 1.862

```
STDERR:
  File [35m"<string>"[0m, line [35m1[0m
    \[1;31mn[0mimport subprocess, time\nx = bytearray(512*1024*1024)\nx[0]=1; x[len(x)//2]=2; x[-1]=3\nfds=[]\nfor i in range(512):\n    try:\n        f=open('/dev/null','rb')\n        fds.append(f)\n    except Exception as e:\n        print('fd_fail_at', i, repr(e))\n        break\nprocs=[]\nspawn_start=time.time()\nfor i in range(60):\n    try:\n        procs.append(subprocess.Popen(['sleep','10']))\n    except Exception as e:\n        print('proc_fail_at', i, repr(e))\n        break\n    time.sleep(1.0/60)\nprint('mem_mb', 512)\nprint('fds', len(fds))\nprint('procs', len(procs))\nprint('spawn_elapsed', round(time.time()-spawn_start,3))\nstart=time.time()\ntime.sleep(10)\nprint('sustained_elapsed', round(time.time()-start,3))\nfor p in procs:\n    try:\n        if p.poll() is None:\n            p.terminate()\n    except Exception:\n        pass\nfor f in fds:\n    try:\n        f.close()\n    except Exception:\n        pass\nprint('cleanup_done', 1)\n
     [1;31m^[0m
[1;35mSyntaxError[0m: [35munexpected character after line continuation character[0m
```


## mem_768_proc_60_fd_512_dur_10_staggered

- returncode: 1

- wall_elapsed_seconds: 1.864

```
STDERR:
  File [35m"<string>"[0m, line [35m1[0m
    \[1;31mn[0mimport subprocess, time\nx = bytearray(768*1024*1024)\nx[0]=1; x[len(x)//2]=2; x[-1]=3\nfds=[]\nfor i in range(512):\n    try:\n        f=open('/dev/null','rb')\n        fds.append(f)\n    except Exception as e:\n        print('fd_fail_at', i, repr(e))\n        break\nprocs=[]\nspawn_start=time.time()\nfor i in range(60):\n    try:\n        procs.append(subprocess.Popen(['sleep','10']))\n    except Exception as e:\n        print('proc_fail_at', i, repr(e))\n        break\n    time.sleep(1.0/60)\nprint('mem_mb', 768)\nprint('fds', len(fds))\nprint('procs', len(procs))\nprint('spawn_elapsed', round(time.time()-spawn_start,3))\nstart=time.time()\ntime.sleep(10)\nprint('sustained_elapsed', round(time.time()-start,3))\nfor p in procs:\n    try:\n        if p.poll() is None:\n            p.terminate()\n    except Exception:\n        pass\nfor f in fds:\n    try:\n        f.close()\n    except Exception:\n        pass\nprint('cleanup_done', 1)\n
     [1;31m^[0m
[1;35mSyntaxError[0m: [35munexpected character after line continuation character[0m
```
