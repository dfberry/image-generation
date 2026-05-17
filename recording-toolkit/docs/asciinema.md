# Asciinema Guide

## Install
```bash
pip install asciinema        # recording tool
cargo install agg            # cast-to-GIF converter
```

## Record
```bash
asciinema rec demo.cast
```

## Convert to GIF
```bash
agg demo.cast demo.gif
```

## Tips
- Keep sessions short (1-3 minutes)
- Use for Azure CLI demos
- asciinema requires WSL on Windows (does not run natively)
- agg works natively on all platforms (Rust binary)
