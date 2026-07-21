from .metamorphosis import MetamorphosisEvent

def register_events(event_manager):
    event_manager.register_event(MetamorphosisEvent())