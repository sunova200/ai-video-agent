import sys, types

class _FakeChain:
    def invoke(self, q):
        return f"Mock answer for: {q}"

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod

_stub("utils", __path__=[])
_stub("utils.audio_processor", process_input=lambda src: ["fake_chunk.wav"])
_stub("core", __path__=[])
_stub("core.transcriber", transcribe_all=lambda chunks, lang="english": "This is a mock transcript about a planning meeting. We decided to launch in Q1.")
_stub("core.summarizer", summarize=lambda t: "- Mock summary bullet", generate_title=lambda t: "Mock Meeting Title")
_stub("core.extractor", extract_action_items=lambda t: "1. Do the thing", extract_key_decisions=lambda t: "1. Chose X", extract_questions=lambda t: "1. When?")
_stub("core.rag_engine", build_rag_chain=lambda t: _FakeChain(), load_rag_chain=lambda: _FakeChain())
_stub("core.vector_store")
