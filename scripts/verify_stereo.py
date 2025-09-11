#!/usr/bin/env python3
"""
Stereo WAV file verification script for SessionScribe dual-channel audio.
Validates that recorded files have proper stereo separation (L=mic, R=system).
"""

import sys
import wave
import math
import argparse
import struct
from pathlib import Path
from typing import Tuple, Dict

def analyze_wav_file(file_path: str) -> Dict:
    """Analyze WAV file and return channel statistics."""
    
    if not Path(file_path).exists():
        raise FileNotFoundError(f"WAV file not found: {file_path}")
    
    with wave.open(file_path, 'rb') as wav_file:
        # Get WAV parameters
        params = wav_file.getparams()
        
        if params.nchannels != 2:
            raise ValueError(f"Expected stereo (2 channels), got {params.nchannels} channels")
        
        if params.sampwidth != 2:
            raise ValueError(f"Expected 16-bit samples, got {params.sampwidth * 8}-bit")
        
        if params.framerate != 48000:
            raise ValueError(f"Expected 48kHz sample rate, got {params.framerate}Hz")
        
        # Read all audio frames
        frames = wav_file.readframes(params.nframes)
        
        # Parse stereo samples (16-bit signed integers)
        samples = struct.unpack(f'<{params.nframes * 2}h', frames)
        
        # Split into left and right channels
        left_channel = samples[0::2]   # Even indices (L=mic)
        right_channel = samples[1::2]  # Odd indices (R=system)
        
        # Calculate RMS (Root Mean Square) for each channel
        def calculate_rms(channel_data):
            if not channel_data:
                return 0.0
            sum_squares = sum(sample ** 2 for sample in channel_data)
            mean_square = sum_squares / len(channel_data)
            return math.sqrt(mean_square)
        
        left_rms = calculate_rms(left_channel)
        right_rms = calculate_rms(right_channel)
        
        # Calculate peak amplitudes
        left_peak = max(abs(sample) for sample in left_channel) if left_channel else 0
        right_peak = max(abs(sample) for sample in right_channel) if right_channel else 0
        
        # Calculate cross-correlation to check for channel mixing
        def calculate_correlation(ch1, ch2, max_samples=48000):  # Use first 1 second
            if len(ch1) == 0 or len(ch2) == 0:
                return 0.0
            
            # Use smaller sample size for performance
            samples_to_use = min(max_samples, len(ch1), len(ch2))
            ch1_sample = ch1[:samples_to_use]
            ch2_sample = ch2[:samples_to_use]
            
            # Normalize samples
            ch1_mean = sum(ch1_sample) / len(ch1_sample)
            ch2_mean = sum(ch2_sample) / len(ch2_sample)
            
            ch1_norm = [s - ch1_mean for s in ch1_sample]
            ch2_norm = [s - ch2_mean for s in ch2_sample]
            
            # Calculate correlation coefficient
            numerator = sum(a * b for a, b in zip(ch1_norm, ch2_norm))
            ch1_var = sum(s ** 2 for s in ch1_norm)
            ch2_var = sum(s ** 2 for s in ch2_norm)
            
            if ch1_var == 0 or ch2_var == 0:
                return 0.0
            
            denominator = math.sqrt(ch1_var * ch2_var)
            return numerator / denominator if denominator != 0 else 0.0
        
        correlation = calculate_correlation(left_channel, right_channel)
        
        return {
            'file_path': file_path,
            'duration_seconds': params.nframes / params.framerate,
            'sample_rate': params.framerate,
            'channels': params.nchannels,
            'bit_depth': params.sampwidth * 8,
            'total_frames': params.nframes,
            'left_rms': left_rms,
            'right_rms': right_rms,
            'left_peak': left_peak,
            'right_peak': right_peak,
            'correlation': correlation
        }

def validate_stereo_separation(stats: Dict, min_separation: float = 0.2, max_correlation: float = 0.8) -> Tuple[bool, str]:
    """Validate that stereo channels have proper separation."""
    
    issues = []
    
    # Check RMS difference between channels
    left_rms = stats['left_rms']
    right_rms = stats['right_rms']
    
    if left_rms == 0 and right_rms == 0:
        issues.append("Both channels are silent")
    elif left_rms == 0:
        issues.append("Left channel (mic) is silent")
    elif right_rms == 0:
        issues.append("Right channel (system) is silent")
    else:
        # Calculate RMS difference ratio
        max_rms = max(left_rms, right_rms)
        min_rms = min(left_rms, right_rms)
        separation_ratio = (max_rms - min_rms) / max_rms
        
        if separation_ratio < min_separation:
            issues.append(f"Channels too similar (separation: {separation_ratio:.3f}, minimum: {min_separation})")
    
    # Check correlation
    correlation = abs(stats['correlation'])
    if correlation > max_correlation:
        issues.append(f"Channels highly correlated (correlation: {correlation:.3f}, maximum: {max_correlation})")
    
    # Check for reasonable audio levels
    left_peak = stats['left_peak']
    right_peak = stats['right_peak']
    
    if left_peak < 1000:  # Very quiet
        issues.append(f"Left channel (mic) very quiet (peak: {left_peak})")
    
    if right_peak < 1000:  # Very quiet
        issues.append(f"Right channel (system) very quiet (peak: {right_peak})")
    
    is_valid = len(issues) == 0
    message = "Stereo separation validated" if is_valid else "; ".join(issues)
    
    return is_valid, message

def main():
    parser = argparse.ArgumentParser(description="Verify stereo WAV file for SessionScribe dual-channel recording")
    parser.add_argument("wav_file", help="Path to stereo WAV file to analyze")
    parser.add_argument("--min-separation", type=float, default=0.2, 
                       help="Minimum RMS separation ratio between channels (default: 0.2)")
    parser.add_argument("--max-correlation", type=float, default=0.8,
                       help="Maximum correlation between channels (default: 0.8)")
    parser.add_argument("--verbose", action="store_true", 
                       help="Show detailed analysis")
    
    args = parser.parse_args()
    
    try:
        # Analyze WAV file
        stats = analyze_wav_file(args.wav_file)
        
        if args.verbose:
            print(f"File: {stats['file_path']}")
            print(f"Duration: {stats['duration_seconds']:.2f} seconds")
            print(f"Format: {stats['sample_rate']}Hz, {stats['bit_depth']}-bit, {stats['channels']} channels")
            print(f"Total frames: {stats['total_frames']:,}")
            print()
            print("Channel Analysis:")
            print(f"  Left (mic) - RMS: {stats['left_rms']:.1f}, Peak: {stats['left_peak']}")
            print(f"  Right (system) - RMS: {stats['right_rms']:.1f}, Peak: {stats['right_peak']}")
            print(f"  Cross-correlation: {stats['correlation']:.3f}")
            print()
        
        # Validate stereo separation
        is_valid, message = validate_stereo_separation(
            stats, 
            args.min_separation, 
            args.max_correlation
        )
        
        if is_valid:
            print(f"✓ PASS: {message}")
            sys.exit(0)
        else:
            print(f"✗ FAIL: {message}")
            sys.exit(1)
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()