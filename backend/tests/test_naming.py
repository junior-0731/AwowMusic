from app.export.naming import format_key, package_name, slug, stem_filename


def test_slug_quita_tildes_espacios_y_simbolos():
    assert slug("Mi canción (demo) #2") == "MiCancionDemo2"
    assert slug("   ") == "Cancion"
    assert slug("ñandú") == "Nandu"


def test_nombre_completo_como_el_plan():
    assert stem_filename("Mi Canción", "Vocals", 95, "Am") == "MiCancion_Vocals_95BPM_Am.wav"


def test_nombre_sin_bpm_ni_tonalidad():
    assert stem_filename("Mi Canción", "Drums") == "MiCancion_Drums.wav"


def test_bpm_decimal_sin_punto():
    assert stem_filename("x", "Bass", 128.5) == "X_Bass_128p5BPM.wav"


def test_tonalidades():
    assert format_key("A minor") == "Am"
    assert format_key("F# m") == "Fsm"
    assert format_key("Bb major") == "Bb"
    assert format_key("C") == "C"
    assert format_key("") is None


def test_nombre_de_paquete():
    assert package_name("Mi Canción", 95, "Am") == "MiCancion_95BPM_Am"
