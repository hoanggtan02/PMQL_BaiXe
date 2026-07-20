import sys

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

bad_fetch_code = """                    async def fetch():
                        async with db.session() as session:
                            s_repo = SQLiteSessionRepository(session)
                            v_repo = SQLiteVehicleRepository(session)
                            l_repo = SQLiteLaneRepository(session)
                            
                            all_sessions = await s_repo.list_recent(settings.branch_id, 5000)
                            v_types = await v_repo.list_all()
                            v_map = {v.code: v.name for v in v_types}
                            lanes = await l_repo.list_by_branch(settings.branch_id)
                            l_map = {l.id: l.name for l in lanes}
                            
                            return all_sessions, v_map, l_map
                    
                    all_sessions, v_map, l_map = asyncio.run(fetch())"""

good_fetch_code = """                    async def fetch():
                        async with db.session() as session:
                            s_repo = SQLiteSessionRepository(session)
                            l_repo = SQLiteLaneRepository(session)
                            
                            all_sessions = await s_repo.list_recent(settings.branch_id, 5000)
                            lanes = await l_repo.list_by_branch(settings.branch_id)
                            l_map = {l.id: l.name for l in lanes}
                            
                            return all_sessions, l_map
                    
                    v_map = asyncio.run(_vehicle_name_map(settings))
                    all_sessions, l_map = asyncio.run(fetch())"""

if bad_fetch_code in content:
    content = content.replace(bad_fetch_code, good_fetch_code)
    with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed SQLiteVehicleRepository error successfully.")
else:
    print("Could not find the target code block. Here is a snippet of the area:")
    idx = content.find("def load_sessions():")
    print(content[idx:idx+800])
