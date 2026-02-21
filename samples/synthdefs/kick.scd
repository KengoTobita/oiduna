// Kick drum SynthDef
SynthDef(\kick, {
    |out=0, freq=50, amp=1.0, decay=0.3|
    var sig, env, freqEnv;

    // Amplitude envelope
    env = EnvGen.kr(Env.perc(0.001, decay), doneAction: 2);

    // Pitch envelope (frequency sweep)
    freqEnv = EnvGen.kr(Env.perc(0.001, 0.1), levelScale: freq * 10, levelBias: freq);

    // Sine oscillator with pitch envelope
    sig = SinOsc.ar(freqEnv);

    // Add some distortion
    sig = (sig * 2).tanh;

    // Output
    Out.ar(out, sig * env * amp ! 2);
}).add;
