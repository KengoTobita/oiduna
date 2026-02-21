// Pad SynthDef
SynthDef(\pad, {
    |out=0, freq=440, gate=1, amp=0.3, cutoff=2000|
    var sig, env;

    // Long attack/release envelope
    env = EnvGen.kr(Env.asr(1.0, 1.0, 2.0), gate, doneAction: 2);

    // Multiple detuned sawtooth oscillators for thickness
    sig = Mix.ar([
        Saw.ar(freq),
        Saw.ar(freq * 1.01),
        Saw.ar(freq * 0.99),
        Saw.ar(freq * 2)
    ]);

    // Low-pass filter
    sig = LPF.ar(sig, cutoff);

    // Output
    Out.ar(out, sig * env * amp ! 2);
}).add;
