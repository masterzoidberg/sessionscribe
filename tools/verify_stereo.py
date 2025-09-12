"""
Stereo WAV Validation Tool
Verify L=mic, R=loopback channel separation with RMS and correlation analysis
"""

import wave
import numpy as np
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple, Any
from datetime import datetime


def load_stereo_wav(file_path: str) -> Tuple[np.ndarray, np.ndarray, int]:
    """Load stereo WAV file and return left, right channels and sample rate"""
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # Validate stereo format
            if wav_file.getnchannels() != 2:
                raise ValueError(f"Expected stereo (2 channels), got {wav_file.getnchannels()}")
            
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            # Read raw audio data
            raw_audio = wav_file.readframes(n_frames)
            
        # Convert to numpy array and separate channels
        # Assuming 16-bit PCM format
        audio_data = np.frombuffer(raw_audio, dtype=np.int16)
        stereo_data = audio_data.reshape(-1, 2)
        
        left_channel = stereo_data[:, 0].astype(np.float32) / 32768.0
        right_channel = stereo_data[:, 1].astype(np.float32) / 32768.0
        
        return left_channel, right_channel, sample_rate
        
    except Exception as e:
        raise RuntimeError(f"Failed to load WAV file {file_path}: {str(e)}")


def compute_rms(signal: np.ndarray) -> float:
    """Compute RMS (Root Mean Square) of audio signal"""
    return float(np.sqrt(np.mean(signal ** 2)))


def compute_cross_correlation(signal1: np.ndarray, signal2: np.ndarray) -> float:
    """Compute normalized cross-correlation between two signals"""
    # Normalize signals
    signal1_norm = (signal1 - np.mean(signal1)) / np.std(signal1)
    signal2_norm = (signal2 - np.mean(signal2)) / np.std(signal2)
    
    # Compute correlation coefficient
    correlation = np.corrcoef(signal1_norm, signal2_norm)[0, 1]
    
    # Handle NaN case (if std is zero)
    if np.isnan(correlation):
        correlation = 0.0
        
    return float(correlation)


def analyze_channel_activity(signal: np.ndarray, sample_rate: int, window_ms: int = 100) -> Dict[str, Any]:
    """Analyze signal activity in time windows"""
    window_samples = int(sample_rate * window_ms / 1000)
    n_windows = len(signal) // window_samples
    
    window_rms_values = []
    active_windows = 0
    silence_threshold = 0.01  # RMS threshold for silence
    
    for i in range(n_windows):
        start_idx = i * window_samples
        end_idx = start_idx + window_samples
        window_signal = signal[start_idx:end_idx]
        
        window_rms = compute_rms(window_signal)
        window_rms_values.append(window_rms)
        
        if window_rms > silence_threshold:
            active_windows += 1
    
    return {
        "total_windows": int(n_windows),
        "active_windows": int(active_windows),
        "activity_ratio": float(active_windows / n_windows if n_windows > 0 else 0.0),
        "mean_rms": float(np.mean(window_rms_values)) if window_rms_values else 0.0,
        "max_rms": float(np.max(window_rms_values)) if window_rms_values else 0.0,
        "silence_ratio": float(1.0 - (active_windows / n_windows) if n_windows > 0 else 1.0)
    }


def validate_stereo_separation(file_path: str) -> Dict[str, Any]:
    """Main validation function - returns validation results as dict"""
    
    validation_result = {
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(),
        "pass": False,
        "details": {},
        "errors": []
    }
    
    try:
        # Load stereo audio
        left_channel, right_channel, sample_rate = load_stereo_wav(file_path)
        
        # Basic file info
        duration_seconds = len(left_channel) / sample_rate
        validation_result["details"]["file_info"] = {
            "sample_rate": int(sample_rate),
            "duration_seconds": round(float(duration_seconds), 2),
            "total_samples": int(len(left_channel))
        }
        
        # Compute overall RMS for each channel
        left_rms = compute_rms(left_channel)
        right_rms = compute_rms(right_channel)
        
        # Compute cross-correlation
        cross_correlation = compute_cross_correlation(left_channel, right_channel)
        
        # Analyze per-channel activity
        left_activity = analyze_channel_activity(left_channel, sample_rate)
        right_activity = analyze_channel_activity(right_channel, sample_rate)
        
        # Store analysis results
        validation_result["details"]["channel_analysis"] = {
            "left_channel": {
                "rms": round(left_rms, 6),
                "activity": left_activity
            },
            "right_channel": {
                "rms": round(right_rms, 6),
                "activity": right_activity
            },
            "cross_correlation": round(cross_correlation, 6)
        }
        
        # Validation criteria (from environment baseline)
        rms_separation_ratio = max(left_rms, right_rms) / (min(left_rms, right_rms) + 1e-8)
        low_correlation_threshold = 0.3  # Baseline requirement
        min_separation_ratio = 5.0  # Baseline requirement: ≥5× RMS split
        
        validation_result["details"]["criteria"] = {
            "rms_separation_ratio": round(float(rms_separation_ratio), 2),
            "cross_correlation_abs": round(float(abs(cross_correlation)), 6),
            "thresholds": {
                "min_separation_ratio": float(min_separation_ratio),
                "max_correlation": float(low_correlation_threshold)
            }
        }
        
        # Apply validation rules
        separation_pass = rms_separation_ratio >= min_separation_ratio
        correlation_pass = abs(cross_correlation) <= low_correlation_threshold
        
        # Additional checks
        both_channels_active = (left_activity["activity_ratio"] > 0.1 and 
                               right_activity["activity_ratio"] > 0.1)
        
        validation_result["details"]["test_results"] = {
            "rms_separation_pass": separation_pass,
            "low_correlation_pass": correlation_pass, 
            "both_channels_active": both_channels_active
        }
        
        # Overall pass/fail
        validation_result["pass"] = separation_pass and correlation_pass and both_channels_active
        
        if not validation_result["pass"]:
            reasons = []
            if not separation_pass:
                reasons.append(f"RMS separation ratio {rms_separation_ratio:.1f} < {min_separation_ratio}")
            if not correlation_pass:
                reasons.append(f"Cross-correlation {abs(cross_correlation):.3f} > {low_correlation_threshold}")
            if not both_channels_active:
                reasons.append(f"Channel activity too low (L:{left_activity['activity_ratio']:.2f}, R:{right_activity['activity_ratio']:.2f})")
            
            validation_result["details"]["failure_reasons"] = reasons
        
        return validation_result
        
    except Exception as e:
        validation_result["errors"].append(str(e))
        return validation_result


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Validate stereo WAV channel separation")
    parser.add_argument("wav_file", help="Path to stereo WAV file")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.wav_file).exists():
        print(f"Error: File not found: {args.wav_file}", file=sys.stderr)
        sys.exit(1)
    
    # Run validation
    try:
        result = validate_stereo_separation(args.wav_file)
        
        # Save to output file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to: {args.output}")
        
        # Print results
        if args.verbose:
            print(json.dumps(result, indent=2))
        else:
            status = "PASS" if result["pass"] else "FAIL" 
            print(f"Validation: {status}")
            
            if result["pass"]:
                details = result["details"]["channel_analysis"]
                print(f"L-channel RMS: {details['left_channel']['rms']:.6f}")
                print(f"R-channel RMS: {details['right_channel']['rms']:.6f}")
                print(f"Cross-correlation: {details['cross_correlation']:.6f}")
            else:
                if "failure_reasons" in result["details"]:
                    for reason in result["details"]["failure_reasons"]:
                        print(f"  - {reason}")
                if result["errors"]:
                    for error in result["errors"]:
                        print(f"  Error: {error}")
        
        # Exit with appropriate code
        sys.exit(0 if result["pass"] else 1)
        
    except Exception as e:
        print(f"Validation failed: {str(e)}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()