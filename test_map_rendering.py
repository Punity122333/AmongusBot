from amongus.map_renderer import MapLayout, MapRenderer, create_map_image

def test_basic_map():
    print("Testing basic map rendering...")
    layout = MapLayout()
    
    img_buffer = create_map_image(
        player_room=None,
        sabotaged_rooms=[],
        map_layout=layout
    )
    
    with open("test_basic_map.png", "wb") as f:
        f.write(img_buffer.read())
    
    print("✅ Basic map saved as test_basic_map.png")

def test_player_location():
    print("\nTesting player location highlighting...")
    layout = MapLayout()
    
    img_buffer = create_map_image(
        player_room="Cafeteria",
        sabotaged_rooms=[],
        map_layout=layout
    )
    
    with open("test_player_location.png", "wb") as f:
        f.write(img_buffer.read())
    
    print("✅ Player location map saved as test_player_location.png")

def test_sabotaged_rooms():
    print("\nTesting sabotaged rooms...")
    layout = MapLayout()
    
    img_buffer = create_map_image(
        player_room="Admin",
        sabotaged_rooms=["Reactor", "O2"],
        map_layout=layout
    )
    
    with open("test_sabotaged.png", "wb") as f:
        f.write(img_buffer.read())
    
    print("✅ Sabotaged map saved as test_sabotaged.png")

def test_bodies():
    print("\nTesting body markers...")
    layout = MapLayout()
    
    layout.add_body_to_room("Electrical", "RedPlayer")
    layout.add_body_to_room("MedBay", "BluePlayer")
    
    img_buffer = create_map_image(
        player_room="Storage",
        sabotaged_rooms=[],
        map_layout=layout
    )
    
    with open("test_bodies.png", "wb") as f:
        f.write(img_buffer.read())
    
    print("✅ Bodies map saved as test_bodies.png")

def test_full_scenario():
    print("\nTesting full game scenario...")
    layout = MapLayout()
    
    # Add bodies
    layout.add_body_to_room("Electrical", "RedPlayer")
    layout.add_body_to_room("Nav", "GreenPlayer")
    
    img_buffer = create_map_image(
        player_room="Cafeteria",
        sabotaged_rooms=["Reactor"],
        map_layout=layout
    )
    
    with open("test_full_scenario.png", "wb") as f:
        f.write(img_buffer.read())
    
    print("✅ Full scenario map saved as test_full_scenario.png")

def test_room_connections():
    print("\nTesting room connections...")
    layout = MapLayout()
    
    cafeteria = layout.get_room("Cafeteria")
    if cafeteria:
        print(f"  Cafeteria connects to: {', '.join(cafeteria.connected_rooms)}")
    
    electrical = layout.get_room("Electrical")
    if electrical:
        print(f"  Electrical connects to: {', '.join(electrical.connected_rooms)}")
        print(f"  Can vent: {electrical.can_vent}")
        print(f"  Has tasks: {electrical.has_tasks}")
        if electrical.task_list:
            print(f"  Tasks: {', '.join(electrical.task_list)}")
    
    print(f"\n  Is Cafeteria connected to Weapons? {layout.is_connected('Cafeteria', 'Weapons')}")
    print(f"  Is Cafeteria connected to Electrical? {layout.is_connected('Cafeteria', 'Electrical')}")

def test_room_metadata():
    print("\nTesting room metadata...")
    layout = MapLayout()
    
    for room_name in ["Electrical", "Cafeteria", "MedBay", "Reactor", "Security"]:
        room = layout.get_room(room_name)
        if room:
            print(f"\n  {room_name}:")
            print(f"    Can vent: {room.can_vent}")
            print(f"    Has tasks: {room.has_tasks}")
            print(f"    Task count: {len(room.task_list)}")
            print(f"    Connected rooms: {len(room.connected_rooms)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Among Us Map Renderer Test Suite")
    print("=" * 60)
    
    test_basic_map()
    test_player_location()
    test_sabotaged_rooms()
    test_bodies()
    test_full_scenario()
    test_room_connections()
    test_room_metadata()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nCheck the generated PNG files to verify the map rendering.")
