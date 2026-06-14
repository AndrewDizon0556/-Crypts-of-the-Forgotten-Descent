"""Combat system: damage formulas, critical hits, status damage."""
from __future__ import annotations

import random

from entities.entity import Entity
from entities.enemy import Enemy, Wraith

CRIT_CHANCE = 0.10


def player_attack(attacker, target: Enemy) -> dict:
    """
    Resolve a player-initiated melee attack on an enemy.
    Returns a result dict: {damage, is_crit, special, killed}.
    """
    raw    = attacker.effective_atk - target.defense + random.randint(-1, 2)
    damage = max(1, raw)

    is_crit = random.random() < CRIT_CHANCE
    if is_crit:
        damage *= 2

    # Rogue backstab passive: 3x damage on first hit of each new enemy
    if getattr(attacker, "backstab_ready", False):
        damage *= 3
        attacker.backstab_ready = False

    target.take_damage(damage)
    return {"damage": damage, "is_crit": is_crit, "killed": not target.alive}


def enemy_attack(attacker: Enemy, target) -> dict:
    """
    Resolve an enemy-initiated attack on the player.
    Handles per-enemy special abilities every 3rd attack.
    Returns {damage, special, killed}.
    """
    attacker.attack_count += 1

    # Wraith ignores defense entirely
    if isinstance(attacker, Wraith):
        raw = attacker.effective_atk + random.randint(-1, 2)
    else:
        raw = attacker.effective_atk - target.effective_defense + random.randint(-1, 2)
    damage = max(1, raw)

    special = None
    if attacker.attack_count % 3 == 0:
        special = attacker.special_ability(target)
        if special == "STUN":
            damage *= 2     # Stone Golem double damage on stun hit

    target.take_damage(damage)
    return {"damage": damage, "special": special, "killed": not target.alive}


def apply_status_damage(entity: Entity) -> int:
    """
    Apply per-turn HP loss from BLEED and POISON.
    Bleed is cured by any heal; poison by Antidote.
    Returns total damage applied this tick.
    """
    total = 0
    for status in entity.status_effects:
        if status.name == "bleed":
            loss = 1
            entity.hp = max(0, entity.hp - loss)
            total += loss
        elif status.name == "poison":
            loss = 2
            entity.hp = max(0, entity.hp - loss)
            total += loss
    if entity.hp == 0:
        entity.alive = False
    return total


def aoe_bomb_damage(player, enemies: list[Enemy], damage: int = 25) -> list[dict]:
    """Deal damage to all enemies adjacent to the player."""
    results = []
    for e in enemies:
        if abs(e.x - player.x) <= 1 and abs(e.y - player.y) <= 1 and e.alive:
            e.take_damage(damage)
            results.append({"enemy": e, "damage": damage, "killed": not e.alive})
    return results


def aoe_fire_scroll_damage(enemies: list[Enemy], damage: int = 12) -> list[dict]:
    """Deal fire damage to every living enemy on the current floor."""
    results = []
    for e in enemies:
        if e.alive:
            e.take_damage(damage)
            results.append({"enemy": e, "damage": damage, "killed": not e.alive})
    return results
