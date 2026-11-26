def test_sonda_falha_de_proposito():
    # Sonda do CI-13: esta PR nunca deve ser mesclada.
    assert False, "falha proposital: o 'CI ok' tem de ficar vermelho"
