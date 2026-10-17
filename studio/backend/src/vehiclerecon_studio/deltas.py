"""Opt-in transport deltas over fully validated core snapshots."""
def snapshot_delta(before,after):
    old={o['id']:o for o in before['observations']};new={o['id']:o for o in after['observations']}
    return {'base_revision':before['revision'],'revision':after['revision'],
            'metadata':{k:v for k,v in after.items() if k!='observations'},
            'upsert':[v for k,v in new.items() if old.get(k)!=v],
            'remove':[k for k in old if k not in new],'order':[o['id'] for o in after['observations']]}
