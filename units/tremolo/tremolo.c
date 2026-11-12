/*
 * Tremolo: amplitude modulation for a stereo pair, free running or locked to the timeline.
 *
 * With a division other than "free" the LFO follows the transport's position in quarter notes
 * (the room's timeline on metalhead.link, Ableton Link or MIDI clock), so every player's
 * tremolo pulses on the same beat. Without a running transport it falls back to `rate`.
 *
 *   [units]
 *   trem Tremolo
 *   [audioroutes]
 *   .Scarlett_2i2_USB:1 trem:1 1.0
 *   trem:1 .Scarlett_2i2_USB:1 1.0
 */
#include <unit_abi.h>
#include <math.h>

#define MAX_INSTANCES   8
#define RAMP_MS         5.0f
#define TWO_PI_F        6.28318530717959f

enum { PARAM_RATE = 1, PARAM_DEPTH, PARAM_DIVISION, PARAM_SHAPE };

// Divisions, in LFO cycles per quarter note; 0 is free running
static const float cyclesPerQuarter[] = { 0, 1, 2, 4, 3 };
static const char * const divisionNames[] = { "free", "1/4", "1/8", "1/16", "1/8T" };
#define NUM_DIVISIONS   (sizeof(cyclesPerQuarter) / sizeof(cyclesPerQuarter[0]))

// Parameter ids are stable: presets and [midimap] lines name them. Never renumber.
static const UnitParamInfo parameters[] = {
    { PARAM_RATE, UNIT_PARAM_IS_AUTOMATABLE, "rate", "lfo", 0.1, 20, 5 },
    { PARAM_DEPTH, UNIT_PARAM_IS_AUTOMATABLE, "depth", "lfo", 0, 100, 50 },
    { PARAM_DIVISION, UNIT_PARAM_IS_STEPPED | UNIT_PARAM_IS_AUTOMATABLE, "division", "sync", 0, NUM_DIVISIONS - 1, 0 },
    { PARAM_SHAPE, UNIT_PARAM_IS_AUTOMATABLE, "shape", "lfo", 0, 100, 0 },
};
#define NUM_PARAMETERS (sizeof(parameters) / sizeof(parameters[0]))

struct Instance {
    int active;
    float rate, depth, division, shape;     // the parameters
    float phase;                            // 0..1
    float depthNow, shapeNow;               // ramped towards the parameters
};

static struct Instance instances[MAX_INSTANCES];
static const UnitHostApi * api;

static float * field(struct Instance * inst, uint32_t id) {
    switch (id) {
    case PARAM_RATE: return &inst->rate;
    case PARAM_DEPTH: return &inst->depth;
    case PARAM_DIVISION: return &inst->division;
    case PARAM_SHAPE: return &inst->shape;
    }
    return 0;
}

static float sampleRateOf(const UnitProcessHost * host) {
    float rate = host ? host->timeInfo.sampleRate : 0;
    return rate >= 8000 && rate <= 384000 ? rate : 48000.0f;
}

static int divisionIndex(float value) {
    int d = (int)(value + 0.5f);
    return d < 0 ? 0 : d >= (int)NUM_DIVISIONS ? (int)NUM_DIVISIONS - 1 : d;
}

static void process(void * instance, UnitProcessHost * host,
                    size_t nrInChannels, float ** inSamples,
                    size_t nrOutChannels, float ** outSamples,
                    size_t frameCount,
                    const UnitParamEvent * paramEvents, size_t paramEventCount) {
    struct Instance * inst = instance;
    if (!inst || nrInChannels < 2 || nrOutChannels < 2 || frameCount == 0) {
        return;
    }
    for (size_t i = 0; i < paramEventCount; i++) {
        float * f = field(inst, paramEvents[i].id);
        if (f) {
            *f = (float)paramEvents[i].value;
        }
    }
    float sampleRate = sampleRateOf(host);
    float k = 1.0f - expf(-1000.0f / (RAMP_MS * sampleRate));

    // Cycles per sample, and for a synced division the phase the transport puts us at
    float cycles = inst->rate / sampleRate;
    float perQuarter = cyclesPerQuarter[divisionIndex(inst->division)];
    if (perQuarter > 0 && host && host->timeInfo.isPlaying && host->timeInfo.tempo > 0) {
        double position = host->timeInfo.ppqPos * perQuarter;
        inst->phase = (float)(position - floor(position));
        cycles = host->timeInfo.tempo / 60.0f * perQuarter / sampleRate;
    }

    float depth = inst->depth * 0.01f;
    float shape = inst->shape * 0.01f;
    for (size_t i = 0; i < frameCount; i++) {
        inst->depthNow += k * (depth - inst->depthNow);
        inst->shapeNow += k * (shape - inst->shapeNow);
        // Sine morphing towards a soft square: the sine pushed through a steeper tanh
        float s = sinf(TWO_PI_F * inst->phase);
        float drive = 1.0f + 9.0f * inst->shapeNow;
        float lfo = tanhf(s * drive) / tanhf(drive);            // -1..1
        float gain = 1.0f - inst->depthNow * 0.5f * (1.0f - lfo);
        outSamples[0][i] = inSamples[0][i] * gain;
        outSamples[1][i] = inSamples[1][i] * gain;
        inst->phase += cycles;
        if (inst->phase >= 1.0f) {
            inst->phase -= 1.0f;
        }
    }
}

static void * createInstance(void) {
    for (int i = 0; i < MAX_INSTANCES; i++) {
        if (!instances[i].active) {
            instances[i] = (struct Instance) { .active = 1, .rate = 5, .depth = 50, .depthNow = 0.5f };
            return &instances[i];
        }
    }
    api->log("Tremolo: no free instances (max %d)", MAX_INSTANCES);
    return 0;
}

static void releaseInstance(void * instance) {
    ((struct Instance *)instance)->active = 0;
}

static uint32_t getNumChannels(void) { return 2; }
static uint32_t getParamCount(void) { return NUM_PARAMETERS; }

static int getParamInfo(uint32_t index, UnitParamInfo * info) {
    if (index >= NUM_PARAMETERS) {
        return 0;
    }
    *info = parameters[index];
    return 1;
}

static int getParamValue(void * instance, uint32_t id, double * value) {
    float * f = field(instance, id);
    if (!f) {
        return 0;
    }
    *value = *f;
    return 1;
}

// The division by name; every other parameter prints as a plain number (return 0)
static int paramValueToText(uint32_t id, double value, char * text, uint32_t size) {
    if (id != PARAM_DIVISION || size == 0) {
        return 0;
    }
    const char * name = divisionNames[divisionIndex((float)value)];
    uint32_t n = 0;
    while (name[n] && n + 1 < size) {
        text[n] = name[n];
        n++;
    }
    text[n] = 0;
    return 1;
}

static int paramTextToValue(uint32_t id, const char * text, double * value) {
    if (id != PARAM_DIVISION) {
        return 0;
    }
    for (uint32_t d = 0; d < NUM_DIVISIONS; d++) {
        const char * a = divisionNames[d];
        const char * b = text;
        while (*a && *a == *b) {
            a++, b++;
        }
        if (!*a && !*b) {
            *value = d;
            return 1;
        }
    }
    return 0;
}

static const UnitPlugin plugin = {
    .size = sizeof(UnitPlugin),
    .name = "Tremolo",
    .vendor = "our band",
    .version = "1.0",
    .description = "Tremolo for a stereo pair, free or locked to the timeline",
    .createInstance = createInstance,
    .releaseInstance = releaseInstance,
    .getNumInputs = getNumChannels,
    .getNumOutputs = getNumChannels,
    .getParamCount = getParamCount,
    .getParamInfo = getParamInfo,
    .getParamValue = getParamValue,
    .paramValueToText = paramValueToText,
    .paramTextToValue = paramTextToValue,
    .process = process,
};

const UnitPlugin * tremolo_plugin(const UnitHostApi * hostApi) {
    api = hostApi;
    return &plugin;
}
