# rip-demo-1

## Host static gemtext files
Place them in the `root` directory and they will automatically be tracked by the server, note that no subdirectories can be made yet.

```bash
git clone https://github.com/4c3e/rip-demo-1
cd rip-demo-1
python3 server/server.py
```

## Connect via RIP browser

```bash
git clone https://github.com/4c3e/rip-demo-1
cd rip-demo-1
python3 client/browser.py
```
Now enter the destination hash created when running the server for the first time.
```bash
> <destination_hash>
```

Add a path to request files besides the `index.gem` file
```bash
> <destination_hash>/about.gem
```
