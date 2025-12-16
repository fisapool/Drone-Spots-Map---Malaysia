#!/bin/bash
# Convert all WebM demo videos to MP4

echo "Checking for ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is not installed."
    echo "Please install it first:"
    echo "  sudo apt install ffmpeg"
    exit 1
fi

echo "Converting WebM files to MP4..."
for file in search_demo*.webm; do
    if [ -f "$file" ]; then
        output="${file%.webm}.mp4"
        echo "Converting: $file -> $output"
        ffmpeg -i "$file" -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart -y "$output"
        if [ $? -eq 0 ]; then
            echo "✓ Success: $output"
        else
            echo "✗ Failed: $file"
        fi
        echo ""
    fi
done

echo "Done!"
