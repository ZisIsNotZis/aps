Transform rules example:
```yaml
burger_job:
  batch_min: 1 # default
  batch_max: 100 # default, can make 100 burger in one batch pass
  consume:
    top:
      type: burger_bun_top
      expiry: $x>$now  # default
      num: 1 # default
      location: local
    bottom:
      type: burger_bun_bottom
      location: local
    stake:
      type: burger_stake
      location: local
    lettuce:
      type: burget_lettuce
      location: local
  consume_batch: # consume in one batch regardless of batch size
    crew:
      type: boh_crew
      lifetime: $x>0 # default
    glove:
      type: disposable_glove
      num: 2
  duration_batch_s: 10 # take on and put off gloves
  duration_s: 5 # time to make each burger
  produce:
    burger:
      type: burger
      expiry: min($top.expiry, $bottom.expiry, $stake.expiry, $lettuce.expiry)
  produce_batch:
    crew: # matches previous key, inherits attribute, so attributes like name don't loss 
      lifetime: $x-1
    glove_waste:
      type: disposable_glove_waste
      num: 2

fries_raw_job:
  batch_max: 10
  consume:
    potato:
      type: cleaned_potato_kg
      num: 1
  consume_batch: # consume in one batch regardless of batch size
    crew:
      type: boh_crew
  duration_s: 5
  produce:
    fries_raw:
      type: fries_raw
      num: 100
  produce_batch:
    crew: # matches previous key, inherits attribute, so attributes like name don't loss 
      lifetime: $x-1

fries_fry_job:
  batch_max: 9999
  consume:
    fries_raw:
      type: fries_raw
      num: 10
  consume_batch: # consume in one batch regardless of batch size
    crew:
      type: boh_crew
    fry_machine:
      type: fry_machine
      state: on
  duration_s: 1 #since duration is too small, we require each item to be 10 fries
  produce:
    fries:
      type: fries
      num: 10
    fry_machine: {}

fry_machine_on:
  consume:
    fry_machine:
      type: fry_machine
      state: off
  produce:
    fry_machine:
      type: fry_machine
      state: on
  duration_s: 600

fry_machine_off:
  consume:
    fry_machine:
      type: fry_machine
      state: on
  produce:
    fry_machine:
      type: fry_machine
      state: off
  duration_s: 300

order_burger_bun_top:
  batch_max: 9999
  consume:
    money:
      type: money_cent
      num: 100
  consume_batch:
    crew:
      type: maintainence_crew
  duration_batch_s: 300s
  produce:
    top:
      type: burger_bun_top
      expiry: $now+30*24*3600
      location: remote
  produce_batch:
    crew: {}

order_burger_stake:
  batch_max: 9999
  consume:
    money:
      type: money_cent
      num: 100
  consume_batch:
    crew:
      type: maintainence_crew
  duration_batch_s: 300s
  produce:
    stake:
      type: burger_stake
      expiry: $now+7*24*3600
      location: remote
  produce_batch:
    crew: {}

transfer_remote_goods:
  batch_max: 9999
  consume:
    remote_stuff:
      location: remote
  consume_rule: sum(i.weight_kg*i.num for i in $consume)<50
  duration_batch_s: 24*3600
  produce:
    remote_stuff:
      localtion: local

garbage_removal:
  batch_max: 9999
  consume:
    glove_waste:
      type: disposable_glove_waste
  duration_batch_s: 60s
  produce: []

crew_need_rest:
  consume:
    crew:
      type: crew # can rest at any time
  duratoin_s: 600s
  produce:
    crew:
      lifetime: 100 # say rest between 100 burgers

electricity:
  consume:
    money:
      type: money_cent
      num: 30
  produce:
    electricity:
      type: electricity_kwh
```

Holding rules example:
```yaml
glove_waste:
  item:
    type: glove_waste
  max: 10

fry_machine:
  item:
    type: fry_machine
    state: on
  consume_per_h:
    elecriticy_kwh: 10

crew_salary:
  item:
    type: $x.match('.*_crew')
  consume_per_h:
    money_cent: 1000
```
