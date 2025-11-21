try:
    import cogs.commands.music
    print("Successfully imported cogs.commands.music")
except ImportError as e:
    print(f"Failed to import cogs.commands.music: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
