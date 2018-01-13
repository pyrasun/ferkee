
import logging

props = {

}

def dump_props():
  log = logging.getLogger(__name__)

  log.info ("Ferkee startup properties:")
  for key, val in props.items():
    if (key == 'from_p'):
      val = "********"
    log.info ("\t%s=%s" % (key, val))

