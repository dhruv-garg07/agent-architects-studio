import os
import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .memory_store import MemoryStore

class FileSystem:
    def __init__(self, store: 'MemoryStore'):
        self.store = store
        
    def _create_node(self, name: str, is_dir: bool, path: str, size: int = 0, date: str = None, type: str = "file", id: str = None):
        return {
            "name": name,
            "path": path.strip("/"),
            "type": "directory" if is_dir else "file",
            "size": size,
            "last_modified": date or datetime.now().isoformat(),
            "content_type": type,
            "id": id
        }

    def list_dir(self, agent_id: str, path: str) -> List[Dict]:
        """
        List contents of a virtual path.
        """
        path = path.strip("/")
        parts = path.split("/") if path else []
        
        # Root
        if not path:
            return [
                self._create_node("Context Store", True, "context"),
                self._create_node("Documents", True, "docs"),
                self._create_node("Checkpoints", True, "checkpoints"),
                self._create_node("Activity Logs", True, "logs")
            ]
            
        category = parts[0].lower()
        
        if category in ["context", "context_store"]:
            if len(parts) == 1:
                return [
                    self._create_node("episodic", True, "context/episodic"),
                    self._create_node("semantic", True, "context/semantic"),
                    self._create_node("procedural", True, "context/procedural"),
                    self._create_node("short_term", True, "context/short_term")
                ]
            else:
                mtype = parts[1]
                items = self.store.db.get_memories(agent_id, mtype, limit=100) or []
                nodes = []
                for item in items:
                    try:
                        ts = str(item.get('created_at', ''))[:19].replace(':', '-') or "unknown"
                        item_id = str(item.get('id', 'unknown'))
                        nodes.append(self._create_node(
                            name=f"{ts}_{item_id}.json",
                            is_dir=False,
                            path=f"context/{mtype}/{ts}_{item_id}.json",
                            size=len(str(item.get('content', ''))),
                            date=item.get('created_at'),
                            type="json",
                            id=item_id
                        ))
                    except: continue
                return nodes
                
        elif category in ["documents", "docs"]:
            if len(parts) == 1:
                return [self._create_node("knowledge", True, "docs/knowledge")]
            else:
                items = self.store.db.get_memories(agent_id, "knowledge", limit=100) or []
                nodes = []
                for item in items:
                    try:
                        item_id = str(item.get('id', 'unknown'))
                        nodes.append(self._create_node(
                            name=f"Doc_{item_id}.md",
                            is_dir=False,
                            path=f"docs/knowledge/Doc_{item_id}.md",
                            size=len(str(item.get('content', ''))),
                            date=item.get('created_at'),
                            type="markdown",
                            id=item_id
                        ))
                    except: continue
                return nodes

        elif category in ["checkpoints", "ckpt"]:
            if len(parts) == 1:
                 return [self._create_node("stable", True, "checkpoints/stable")]
            else:
                c_type = parts[1]
                items = self.store.db.get_checkpoints(agent_id, c_type, limit=50) or []
                nodes = []
                for item in items:
                    try:
                        ts = str(item.get('created_at', ''))[:19].replace(':', '-') or "unknown"
                        item_id = str(item.get('id', 'unknown'))
                        nodes.append(self._create_node(
                            name=f"Checkpoint_{ts}_{item_id}.json",
                            is_dir=False,
                            path=f"checkpoints/{c_type}/Checkpoint_{ts}_{item_id}.json",
                            size=len(str(item.get('state_dump', ''))),
                            date=item.get('created_at'),
                            type="json",
                            id=item_id
                        ))
                    except: continue
                return nodes
                
        elif category in ["activity_logs", "logs"]:
            if len(parts) == 1:
                return [self._create_node("system", True, "logs/system")]
            else:
                l_type = parts[1]
                items = self.store.db.get_logs(agent_id, l_type, limit=100) or []
                nodes = []
                for item in items:
                    try:
                        ts = str(item.get('created_at', ''))[:19].replace(':', '-') or "unknown"
                        item_id = str(item.get('id', 'unknown'))
                        nodes.append(self._create_node(
                            name=f"Log_{ts}_{item_id}.txt",
                            is_dir=False,
                            path=f"logs/system/Log_{ts}_{item_id}.txt",
                            size=len(str(item.get('event', ''))),
                            date=item.get('created_at'),
                            type="text",
                            id=item_id
                        ))
                    except: continue
                return nodes
                
        elif category in ["vectors", "vec"]:
            if len(parts) == 1:
                 return [self._create_node("index", True, "vectors/index")]
            else:
                 # vectors/index
                 if getattr(self.store, 'vector_engine', None):
                     # Fetch vectors
                     vectors = self.store.vector_engine.get_agent_vectors(agent_id, limit=100)
                     nodes = []
                     for v in vectors:
                         vid = v.get('id')
                         nodes.append(self._create_node(
                             name=f"Vector_{vid}.json",
                             is_dir=False,
                             path=f"vectors/index/Vector_{vid}.json",
                             size=len(str(v.get('content', ''))),
                             date=str(v.get('metadata', {}).get('timestamp', datetime.now().isoformat())),
                             type="vector",
                             id=vid
                         ))
                     return nodes
                 return []
                
        return []

    def read_file(self, agent_id: str, virtual_path: str) -> Optional[Dict]:
        """
        Get file content. 
        Virtual path is less useful here because filenames contain IDs.
        We expect the UI to pass the ID via a separate mechanism or we parse it from filename?
        Ideally, the route calling this handles ID resolution.
        But if strict path implementation:
        Format: /category/type/filename(ID)
        """
        path = virtual_path.strip("/")
        parts = path.split("/")
        if len(parts) < 3: return None
        
        category = parts[0].lower().replace(" ", "_")
        subtype = parts[1]
        filename = parts[2]
        
        # Extract ID from filename (assuming format ..._ID.ext)
        # Or simplistic approach: pass ID in query param, but method signature is path.
        # Let's extract: Split by '_' last part, then split '.' 
        # CAUTION: UUIDs might not be simple.
        # Better: Since list_dir returned specific nodes with IDs, 
        # we can search again or just look up directly if we knew the table.
        # Using ID encoded in filename suffix before extension.
        
        try:
            file_id_part = filename.rsplit('_', 1)[-1] # ID.json
            item_id = file_id_part.split('.')[0]
        except:
            return None
            
        if category in ["context", "context_store"]:
             res = self.store.db.client.table('gitmem_memories').select('*').eq('id', item_id).execute()
             if res.data:
                 return {
                     "content": json.dumps(res.data[0], indent=2, sort_keys=True),
                     "metadata": res.data[0].get('metadata', {}),
                     "type": "json"
                 }

        elif category in ["documents", "docs"]:
             res = self.store.db.client.table('gitmem_memories').select('*').eq('id', item_id).execute()
             if res.data:
                 return {
                     "content": res.data[0]['content'], 
                     "metadata": res.data[0].get('metadata', {}),
                     "type": "markdown"
                 }

        elif category in ["checkpoints", "ckpt"]:
             res = self.store.db.client.table('gitmem_checkpoints').select('*').eq('id', item_id).execute()
             if res.data:
                 return {
                     "content": json.dumps(res.data[0]['state_dump'], indent=2),
                     "metadata": res.data[0].get('metadata'),
                     "type": "json"
                 }
                 
        elif category in ["activity_logs", "logs"]:
             res = self.store.db.client.table('gitmem_logs').select('*').eq('id', item_id).execute()
             if res.data:
                 # Logs might have 'event' and 'details'
                 row = res.data[0]
                 text = f"{row['created_at']} - {row['event']}\n\nDetails:\n{json.dumps(row.get('details'), indent=2)}"
                 return {
                     "content": text,
                     "metadata": {},
                     "type": "text"
                 }

        elif category in ["vectors", "vec"]:
             # Extract ID from filename: Vector_<ID>.json
             try:
                 temp = filename.rsplit('.', 1)[0]
                 if temp.startswith("Vector_"):
                      vid = temp[7:]
                 else:
                      vid = temp
                 
                 if getattr(self.store, 'vector_engine', None):
                      v_data = self.store.vector_engine.get_vector(vid, agent_id=agent_id)
                      if v_data:
                           return {
                               "content": json.dumps(v_data, indent=2),
                               "metadata": v_data.get('metadata', {}),
                               "type": "json"
                           }
             except: pass
                 
        return None
