// Acid bass SynthDef
SynthDef(\acid, {
    |out=0, freq=440, gate=1, amp=0.5, cutoff=1000, res=0.5|
    var sig, env, filterEnv;

    // Envelope
    env = EnvGen.kr(Env.adsr(0.01, 0.1, 0.5, 0.2), gate, doneAction: 2);

    // Filter envelope
    filterEnv = EnvGen.kr(Env.adsr(0.01, 0.2, 0.2, 0.3), gate);

    // Sawtooth oscillator
    sig = Saw.ar(freq);

    // Resonant low-pass filter
    sig = RLPF.ar(sig, cutoff * filterEnv + 100, res);

    // Output
    Out.ar(out, sig * env * amp ! 2);
}).add;
