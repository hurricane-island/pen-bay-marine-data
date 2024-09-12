Problem description
    title = "Hurricane Scientific Mooring"
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
    depth = 100
    density = 1025.0
    gravity = 9.81
    bottom-stiffness = 100
    bottom-damping = 1
    x-current = 0.257
    current-scale = 1.000
    forcing-method = wave-follower
    input-type = random
    x-wave = (1.22, 8.00, 0)

Layout
    terminal = {
       anchor = clump
    safety = 2.00
    mu = 1.00
       x = 0
       y = 0
       z = 0
    }
    segment = {
        length = 3
        material = chain
        nodes = (25, 1)
    }
    segment = {
        length = 144
        material = yalex_3/8in
        nodes = (150, 1)
    }
    segment = {
        length = 3
        material = chain
        nodes = (25, 1)
    }
    terminal = {
       buoy = float
       x = 0
       y = 0
       z = 0
    }

Buoys
    float
        type=cylinder
        mass=23
        diam=0.9144
        height=0.2032
        Cdt=0
        Cdn=1
        buoyancy=0
        Cdw=0
        Sw=0

Anchors
    clump
        mass=0
        wet=0
        diam=0
        Cdt=0
        Cdn=0
        mu=0

Connectors

Materials
    chain
        type=linear
        mass=4.4
        wet=38.1
        diam=0.0265
        length=0
        Cdn=1
        Cdt=0.01
        amn=0.584
        amt=0
        EA=5.5e+007
        EI=0.01
        GJ=0.1
        SWL=0
        yield=0
    yalex_3/8in
        type=linear
        mass=0.058
        wet=0.146
        diam=0.00953
        length=0
        Cdn=1.5
        Cdt=0.005
        amn=0
        amt=0
        EA=129840
        EI=0.01
        GJ=0.01
        SWL=0
        yield=0


End
