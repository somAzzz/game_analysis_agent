class_name CharacterDef
extends Resource

@export var id: String = ""
@export var name: String = ""
@export var role: String = ""
@export_multiline var description: String = ""
@export var starting_relationship: Dictionary = {"favorability": 20, "trust": 10, "conflict": 0, "story_stage": 0}
