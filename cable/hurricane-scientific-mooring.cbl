Problem description
    title = "Hurricane Island Scientific Mooring"
    type = surface

Analysis parameters
    static-relaxation = 0.01
    static-iterations = 2000
    static-tolerance = 0.0001
    static-outer-relaxation = 0.800
    static-outer-iterations = 100
    static-outer-tolerance = 0.01
    dynamic-relaxation = 1.000
    dynamic-iterations = 50
    dynamic-tolerance = 1e-006
    time-step = 0.0100
    duration = 120
    ramp-time = 16
    static-outer-method = bisection
    dynamic-integration = spatial
    static-initial-guess = shooting
    static-solution = relaxation

Environment
    depth = 11
    density = 1025.0
    gravity = 9.81
    bottom-stiffness = 100
    bottom-damping = 1
    x-current = {"3_knot_linear_10"} (0.00, 1.50)(11.00, 0.00)
    x-wind = 1.5
    current-scale = 1.000
    forcing-method = wave-follower
    input-type = random
    x-wave = (1.00, 10.00, 0)

Layout
    terminal = {
       anchor = dormor_135lbs
       safety = 10.00
       mu = 1.00
       x = 0
       y = 0
       z = 0
    }
    segment = {
        length = 2.5
        material = chain_1/2in
        nodes = (25, 1)
    }
    segment = {
        length = 12.5
        material = yale_nylon_brait_3/8in
        nodes = (125, 1)
    }
    segment = {
        length = 1.5
        material = chain_1/2in
        nodes = (15, 1)
    }
    terminal = {
       buoy = db600
       x = 0
       y = 0
       z = 0
    }

Buoys
    db600
        type=cylinder
        mass=30
        diam=0.6
        height=0.35
        Cdt=0
        Cdn=1
        buoyancy=0
        Cdw=1
        Sw=0

Anchors
    dormor_135lbs
        mass=0
        wet=0
        diam=0
        Cdt=0
        Cdn=0
        mu=0

Connectors

Materials
    chain_1/2in
        type=linear
        mass=4.091
        wet=34.8878
        diam=0.0475
        length=0
        Cdn=0.55
        Cdt=0.05
        amn=0
        amt=0
        EA=6e+007
        EI=0.0001
        GJ=0.0001
        SWL=0
        yield=0
    yale_nylon_brait_3/8in
        type=linear
        mass=0.057
        wet=0
        diam=0.00953
        length=0
        Cdn=1.5
        Cdt=0.005
        amn=0
        amt=0
        EA=129840
        EI=0.01
        GJ=0.01
        SWL=1780
        yield=8896


End
