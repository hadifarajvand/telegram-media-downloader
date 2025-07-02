# Telegram Media Downloader - Enhanced Version

A robust, feature-rich Python tool for downloading media files from Telegram channels and groups with advanced capabilities including resume functionality, CLI support, progress tracking, and intelligent file organization.

## 🚀 New Features in Enhanced Version

### Core Improvements
- **✅ Resume Downloads**: Automatically resumes interrupted downloads
- **✅ CLI Interface**: Full command-line support with Click
- **✅ Rich UI**: Beautiful progress bars and tables with Rich
- **✅ Configuration File**: YAML-based configuration system
- **✅ Advanced Logging**: Comprehensive logging with rotation
- **✅ Error Handling**: Robust error handling with retry mechanisms
- **✅ File Deduplication**: Prevents downloading the same file twice
- **✅ Metadata Preservation**: Saves message metadata alongside files

### Download Features
- **✅ Batch Processing**: Configurable concurrent downloads
- **✅ File Filtering**: Size and extension-based filtering
- **✅ Speed Limiting**: Configurable download speed limits
- **✅ File Organization**: Channel and date-based organization
- **✅ Dry Run Mode**: Preview downloads without actually downloading
- **✅ Progress Tracking**: Real-time progress with ETA and speed

### Security & Safety
- **✅ File Size Limits**: Configurable maximum file sizes
- **✅ Extension Filtering**: Whitelist/blacklist file extensions
- **✅ Safe Filenames**: Automatic filename sanitization
- **✅ Backup Prevention**: Prevents overwriting existing files

## 📋 Requirements

- Python 3.8+
- Telegram API credentials (API ID and API Hash)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/telegram-media-downloader.git
   cd telegram-media-downloader
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**:
   Create a `.env` file:
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   ```

4. **Configure settings** (optional):
   The script will create a `config.yaml` file on first run, or you can create it manually.

## 🎯 Usage

### Basic Usage

```bash
# Interactive mode
python src/downloader.py

# Command line mode
python src/downloader.py --channel @channel_name --type videos --limit 100
```

### CLI Options

```bash
python src/downloader.py [OPTIONS]

Options:
  -c, --channel TEXT     Channel username or link
  -t, --type [images|videos|pdfs|zips|documents|all]
                         Type of media to download
  -l, --limit INTEGER    Maximum number of messages to fetch [default: 2000]
  -b, --batch-size INTEGER
                         Number of concurrent downloads [default: 5]
  -o, --output TEXT      Output directory [default: downloads]
  --dry-run             Show what would be downloaded without actually downloading
  --resume              Resume from previous download state
  --help                Show this message and exit
```

### Examples

```bash
# Download all videos from a channel
python src/downloader.py -c @my_channel -t videos -l 500

# Download images with custom batch size
python src/downloader.py -c @photo_channel -t images -b 10

# Preview what would be downloaded
python src/downloader.py -c @test_channel -t all --dry-run

# Resume interrupted downloads
python src/downloader.py -c @channel -t documents --resume

# Download to custom directory
python src/downloader.py -c @channel -t pdfs -o /path/to/downloads
```

## ⚙️ Configuration

The downloader uses a `config.yaml` file for advanced configuration:

```yaml
# Telegram API Configuration
telegram:
  session_name: "default_session"
  batch_size: 5
  max_retries: 3
  retry_delay: 5

# Download Settings
download:
  output_directory: "downloads"
  max_file_size_mb: 1000  # 1GB limit
  download_speed_limit: 0  # 0 = no limit
  preserve_metadata: true
  organize_by_date: false
  organize_by_channel: true

# Filtering
filters:
  min_file_size_kb: 0
  max_file_size_mb: 1000
  allowed_extensions: []  # Empty = all extensions
  excluded_extensions: [".exe", ".bat", ".sh"]

# Logging
logging:
  level: "INFO"
  file: "telegram_downloader.log"
  max_size_mb: 10
  backup_count: 5

# UI Settings
ui:
  show_progress: true
  show_file_info: true
  colors: true
  quiet_mode: false
```

## 📁 File Organization

The downloader organizes files intelligently:

```
downloads/
├── channel_name/
│   ├── images/
│   │   ├── photo_123.jpg
│   │   └── photo_123.jpg.json  # Metadata
│   ├── videos/
│   │   ├── video_456.mp4
│   │   └── video_456.mp4.json
│   └── documents/
│       ├── document_789.pdf
│       └── document_789.pdf.json
```

## 🔄 Resume Functionality

The downloader automatically tracks downloaded files in `download_state.json`:

- **Automatic Resume**: Restart the script to resume from where it left off
- **State Persistence**: Download state is saved between sessions
- **File Deduplication**: Already downloaded files are automatically skipped

## 📊 Progress Tracking

Real-time progress information includes:

- **File Progress**: Individual file download progress
- **Batch Progress**: Overall batch completion
- **Speed Information**: Download speed in MB/s
- **ETA**: Estimated time remaining
- **Statistics**: Success/failure counts

## 🛡️ Safety Features

### File Size Limits
- Configurable maximum file size to prevent downloading massive files
- Minimum file size filtering for small files

### Extension Filtering
- Whitelist specific file extensions
- Blacklist dangerous extensions (.exe, .bat, etc.)

### Safe Filenames
- Automatic sanitization of filenames
- Prevention of path traversal attacks
- Backup filename generation for conflicts

## 📝 Logging

Comprehensive logging system:

- **File Logging**: Rotated log files with size limits
- **Console Output**: Rich formatted output
- **Error Tracking**: Detailed error information
- **Download History**: Complete download history

## 🔧 Advanced Features

### Metadata Preservation
Each downloaded file gets a corresponding `.json` file with:
- Message ID and date
- Sender information
- File size and hash
- Download timestamp

### Batch Processing
- Configurable batch sizes for optimal performance
- Parallel downloads with progress tracking
- Automatic retry on failures

### Error Handling
- Network error recovery
- Rate limiting compliance
- Graceful failure handling
- Partial file cleanup

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Ensure API_ID and API_HASH are correct
   - Check your `.env` file format

2. **Download Failures**:
   - Check network connection
   - Verify channel accessibility
   - Review log files for details

3. **Memory Issues**:
   - Reduce batch size in config
   - Lower message limit
   - Use dry-run mode first

### Log Files
- Check `telegram_downloader.log` for detailed error information
- Log rotation prevents disk space issues

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram API client
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [Click](https://github.com/pallets/click) - CLI framework
- [Tenacity](https://github.com/jd/tenacity) - Retry logic

---

**Enhanced with ❤️ for better Telegram media management** 