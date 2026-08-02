import wave
import struct
import os

def create_notification_sound():
    sounds_dir = os.path.join(os.path.dirname(__file__), "app", "sounds")
    os.makedirs(sounds_dir, exist_ok=True)
    
    sound_file = os.path.join(sounds_dir, "complete.wav")
    
    sample_rate = 44100
    duration = 0.8
    
    frequencies = [523.25, 659.25, 783.99, 1046.50]
    
    with wave.open(sound_file, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        total_samples = int(sample_rate * duration)
        
        for i in range(total_samples):
            t = float(i) / sample_rate
            
            value = 0
            for j, freq in enumerate(frequencies):
                note_duration = duration / len(frequencies)
                note_start = j * note_duration
                note_end = (j + 1) * note_duration
                
                if note_start <= t < note_end:
                    note_t = t - note_start
                    envelope = 1.0 - (note_t / note_duration)
                    envelope = max(0, envelope ** 2)
                    value += 0.25 * envelope * (1 if (note_t * freq * 2) % 1 < 0.5 else -1)
            
            value = int(32767.0 * min(1.0, max(-1.0, value)))
            data = struct.pack('<h', value)
            wav_file.writeframes(data)
    
    print(f"Created notification sound: {sound_file}")

if __name__ == "__main__":
    create_notification_sound()
