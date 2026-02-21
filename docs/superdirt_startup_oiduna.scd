/*
Oiduna-compatible SuperDirt startup script

This script extends the standard SuperDirt startup to support Oiduna's asset management.

Installation:
1. Copy this file to: ~/Library/Application Support/SuperCollider/
   (or Platform.userAppSupportDir +/+ "superdirt_startup_oiduna.scd")
2. Load it from your startup.scd:
   "~/Library/Application Support/SuperCollider/superdirt_startup_oiduna.scd".load;
3. Update OIDUNA_DATA_PATH to match your Oiduna installation

Features:
- Loads default Dirt-Samples
- Loads custom samples from Oiduna
- Watches Oiduna directories for new files
- Automatically loads new SynthDefs
*/

(
// ★ Configure this path to your Oiduna data directory
~oidunaDataPath = "/path/to/oiduna_data".standardizePath;  // UPDATE THIS!

s.reboot {
	// Server options
	s.options.numBuffers = 1024 * 256;
	s.options.memSize = 8192 * 32;
	s.options.numWireBufs = 2048;
	s.options.maxNodes = 1024 * 32;
	s.options.numOutputBusChannels = 2;
	s.options.numInputBusChannels = 2;

	s.waitForBoot {
		~dirt.stop; // Stop any old instance
		~dirt = SuperDirt(2, s);

		// Load default Dirt-Samples
		~dirt.loadSoundFiles;

		// ★ Load Oiduna custom samples
		if(File.exists(~oidunaDataPath +/+ "samples")) {
			"Loading Oiduna samples from: %".format(~oidunaDataPath +/+ "samples/*").postln;
			~dirt.loadSoundFiles(~oidunaDataPath +/+ "samples/*");
		} {
			"⚠ Oiduna samples directory not found: %".format(~oidunaDataPath +/+ "samples").warn;
		};

		// ★ Watch Oiduna samples directory for new files
		if(File.exists(~oidunaDataPath +/+ "samples")) {
			~oidunaSampleWatcher = PathWatcher.new(~oidunaDataPath +/+ "samples").watch({
				|path|
				// Reload when new .wav/.aiff files are added
				if(path.endsWith(".wav") || path.endsWith(".aiff") || path.endsWith(".aif") || path.endsWith(".aifc")) {
					"🔄 Oiduna: New sample detected, reloading...".postln;
					fork {
						1.wait; // Wait for file to be fully written
						~dirt.loadSoundFiles(~oidunaDataPath +/+ "samples/*");
						"✓ Samples reloaded".postln;
					};
				};
			});
			"✓ Watching Oiduna samples directory".postln;
		};

		// ★ Watch Oiduna SynthDefs directory
		if(File.exists(~oidunaDataPath +/+ "synthdefs")) {
			~oidunaSynthDefWatcher = PathWatcher.new(~oidunaDataPath +/+ "synthdefs").watch({
				|path|
				if(path.endsWith(".scd")) {
					"🔄 Oiduna: Loading SynthDef: %".format(path).postln;
					fork {
						0.5.wait; // Wait for file to be fully written
						try {
							path.load;
							"✓ SynthDef loaded: %".format(path.basename).postln;
						} {
							|error|
							"⚠ Failed to load SynthDef: %\n%".format(path, error).warn;
						};
					};
				};
			});
			"✓ Watching Oiduna SynthDefs directory".postln;
		};

		// Start SuperDirt
		~dirt.start(57120, 0 ! 12);
		SuperDirt.default = ~dirt;

		// Optional: convenient access to orbits
		(
			~d1 = ~dirt.orbits[0]; ~d2 = ~dirt.orbits[1]; ~d3 = ~dirt.orbits[2];
			~d4 = ~dirt.orbits[3]; ~d5 = ~dirt.orbits[4]; ~d6 = ~dirt.orbits[5];
			~d7 = ~dirt.orbits[6]; ~d8 = ~dirt.orbits[7]; ~d9 = ~dirt.orbits[8];
			~d10 = ~dirt.orbits[9]; ~d11 = ~dirt.orbits[10]; ~d12 = ~dirt.orbits[11];
		);

		"".postln;
		"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
		"✓ SuperDirt started with Oiduna integration".postln;
		"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".postln;
		"".postln;
		"Oiduna data directory: %".format(~oidunaDataPath).postln;
		"Samples: % categories".format(
			(~oidunaDataPath +/+ "samples/*").pathMatch.size
		).postln;
		"".postln;
	};

	s.latency = 0.3;
};
);

/*
Usage example:

1. Upload a sample via Oiduna API:
   curl -X POST http://localhost:57122/assets/samples \
     -F "file=@my_kick.wav" \
     -F "category=kicks"

2. SuperDirt will automatically detect and load it

3. Use it in Oiduna pattern:
   {
     "tracks": {
       "custom": {
         "sound": "kicks",  ← Your category name
         "orbit": 0,
         "sequence": [...]
       }
     }
   }
*/
