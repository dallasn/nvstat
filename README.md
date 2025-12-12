# nvstat

A lightweight CLI tool for monitoring NVIDIA GPUs with ASCII bar charts and gauges. Similar to `nvtop` but simpler and runs entirely in the terminal with no external dependencies.

![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Real-time GPU monitoring** - Polls nvidia-smi every 2 seconds
- **ASCII bar charts** for each GPU showing:
  - Temperature (color-coded: green/yellow/red)
  - GPU Utilization
  - Memory Usage
  - Power Draw
- **Aggregate gauges** showing:
  - Total VRAM usage
  - Average GPU utilization
  - Total power consumption
  - Average temperature
- **Dynamic terminal sizing** - Adapts to terminal width (80-160 columns)
- **Multi-GPU support** - Displays all detected NVIDIA GPUs
- **Zero dependencies** - Uses only Python standard library

## Requirements

- Python 3.6+
- NVIDIA GPU with drivers installed
- `nvidia-smi` available in PATH

## Installation

```bash
# Clone the repository
git clone https://github.com/dallasn/nvstat.git
cd nvstat

# Make executable
chmod +x nvstat.py

# Optionally, copy to your PATH
sudo cp nvstat.py /usr/local/bin/nvstat
```

## Usage

```bash
# Run directly
./nvstat.py

# Or if installed to PATH
nvstat
```

Press `Ctrl+C` to exit.

## Color Coding

- **Green**: Normal/Good (temp < 60°C, usage < 70%)
- **Yellow**: Warning (temp 60-80°C, usage 70-90%)
- **Red**: Critical (temp > 80°C, usage > 90%)
- **Cyan**: Neutral (GPU utilization bars)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
