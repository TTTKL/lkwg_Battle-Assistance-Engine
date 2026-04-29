from data_loader import DataLoader


loader = DataLoader()
loader.load_type_chart()


def _find_attacker_with_multiplier(target_multiplier: float):
    for attacker in loader.types:
        matches = []
        for defender in loader.types:
            if loader.get_type_effectiveness(attacker, defender) == target_multiplier:
                matches.append(defender)
        if len(matches) >= 2:
            return attacker, matches[0], matches[1]
    raise AssertionError(f"Could not find attacker with two {target_multiplier}x matchups")


strong_attacker, strong_def1, strong_def2 = _find_attacker_with_multiplier(2)
weak_attacker, weak_def1, weak_def2 = _find_attacker_with_multiplier(0.5)


double_super = loader.get_combined_type_effectiveness(strong_attacker, [strong_def1, strong_def2])
assert double_super == 3.0, double_super

double_resist = loader.get_combined_type_effectiveness(weak_attacker, [weak_def1, weak_def2])
assert double_resist == 0.25, double_resist

dedup_same_type = loader.get_combined_type_effectiveness(strong_attacker, [strong_def1, strong_def1])
assert dedup_same_type == 2.0, dedup_same_type

print("type effectiveness rules ok")
