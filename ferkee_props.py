
props = {

}

def dump_props():
  print ("Ferkee startup properties:")
  for key, val in props.items():
    if (key == 'from_p'):
      val = "********"
    print ("\t%s=%s" % (key, val))

