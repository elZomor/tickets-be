def only_third_side(endpoints, **kwargs):
    """Keep the generated schema scoped to the Third Side contract."""
    return [e for e in endpoints if e[0].startswith('/third_side/')]
