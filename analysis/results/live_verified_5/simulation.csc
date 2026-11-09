<?xml version='1.0' encoding='UTF-8'?>
<simconf version="2023090701">
  <simulation>
    <title>WSN temperature / 5 sensors</title>
    <randomseed>123456</randomseed>
    <speedlimit>1.0</speedlimit>
    <motedelay_us>0</motedelay_us>
    <radiomedium>org.contikios.cooja.radiomediums.UDGM<transmitting_range>50</transmitting_range>
      <interference_range>100</interference_range>
      <success_ratio_tx>1</success_ratio_tx>
      <success_ratio_rx>1.0</success_ratio_rx>
    </radiomedium>
    <motetype>org.contikios.cooja.contikimote.ContikiMoteType<identifier>wsnsink</identifier>
      <description>sink_node</description>
      <source>[CONFIG_DIR]/../sink-node/sink_node.c</source>
      <commands>$(MAKE) -j1 sink_node.cooja TARGET=cooja</commands>
      <moteinterface>org.contikios.cooja.interfaces.Position</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiMoteID</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiRS232</moteinterface>
      <moteinterface>org.contikios.cooja.interfaces.RimeAddress</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiIPAddress</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiRadio</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiClock</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiLED</moteinterface>
      <moteinterface>org.contikios.cooja.interfaces.Mote2MoteRelations</moteinterface>
      <moteinterface>org.contikios.cooja.interfaces.MoteAttributes</moteinterface>
    </motetype>
    <motetype>org.contikios.cooja.contikimote.ContikiMoteType<identifier>wsnsensor</identifier>
      <description>temperature_sensor</description>
      <source>[CONFIG_DIR]/../temperature-sensor/temperature_sensor.c</source>
      <commands>$(MAKE) -j1 temperature_sensor.cooja TARGET=cooja</commands>
      <moteinterface>org.contikios.cooja.interfaces.Position</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiMoteID</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiRS232</moteinterface>
      <moteinterface>org.contikios.cooja.interfaces.RimeAddress</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiIPAddress</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiRadio</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiClock</moteinterface>
      <moteinterface>org.contikios.cooja.contikimote.interfaces.ContikiLED</moteinterface>
      <moteinterface>org.contikios.cooja.interfaces.Mote2MoteRelations</moteinterface>
      <moteinterface>org.contikios.cooja.interfaces.MoteAttributes</moteinterface>
    </motetype>
    <mote>
      <interface_config>org.contikios.cooja.interfaces.Position<x>0</x>
        <y>0</y>
        <z>0</z>
      </interface_config>
      <interface_config>org.contikios.cooja.contikimote.interfaces.ContikiMoteID<id>1</id>
      </interface_config>
      <motetype_identifier>wsnsink</motetype_identifier>
    </mote>
    <mote>
      <interface_config>org.contikios.cooja.interfaces.Position<x>35</x>
        <y>0</y>
        <z>0</z>
      </interface_config>
      <interface_config>org.contikios.cooja.contikimote.interfaces.ContikiMoteID<id>2</id>
      </interface_config>
      <motetype_identifier>wsnsensor</motetype_identifier>
    </mote>
    <mote>
      <interface_config>org.contikios.cooja.interfaces.Position<x>35</x>
        <y>25</y>
        <z>0</z>
      </interface_config>
      <interface_config>org.contikios.cooja.contikimote.interfaces.ContikiMoteID<id>3</id>
      </interface_config>
      <motetype_identifier>wsnsensor</motetype_identifier>
    </mote>
    <mote>
      <interface_config>org.contikios.cooja.interfaces.Position<x>70</x>
        <y>0</y>
        <z>0</z>
      </interface_config>
      <interface_config>org.contikios.cooja.contikimote.interfaces.ContikiMoteID<id>4</id>
      </interface_config>
      <motetype_identifier>wsnsensor</motetype_identifier>
    </mote>
    <mote>
      <interface_config>org.contikios.cooja.interfaces.Position<x>70</x>
        <y>25</y>
        <z>0</z>
      </interface_config>
      <interface_config>org.contikios.cooja.contikimote.interfaces.ContikiMoteID<id>5</id>
      </interface_config>
      <motetype_identifier>wsnsensor</motetype_identifier>
    </mote>
    <mote>
      <interface_config>org.contikios.cooja.interfaces.Position<x>105</x>
        <y>0</y>
        <z>0</z>
      </interface_config>
      <interface_config>org.contikios.cooja.contikimote.interfaces.ContikiMoteID<id>6</id>
      </interface_config>
      <motetype_identifier>wsnsensor</motetype_identifier>
    </mote>
  </simulation>
  <plugin>org.contikios.cooja.plugins.ScriptRunner<plugin_config>
      <script>sim.setSpeedLimit(1.0);
wsnSeen = {};
wsnMultihop = false;
wsnFinish = function() {
  log.log('WSN_META ' + JSON.stringify({type:'end', sim_time_us:60000000, received_nodes:Object.keys(wsnSeen).length, multihop:wsnMultihop}) + '\n');
  if(Object.keys(wsnSeen).length == 5 &amp;&amp; wsnMultihop) log.testOK(); else log.testFailed();
};
TIMEOUT(60000, wsnFinish());
while(true) {
  var line = String(msg);
  log.log('WSN_EVENT ' + JSON.stringify({sim_time_us:time, mote_id:id, message:line}) + '\n');
  if(line.charAt(0) == '{') {
    try {
      var event = JSON.parse(line);
      if(event.type == 'rx') wsnSeen[event.node_id] = true;
      if(event.type == 'status' &amp;&amp; event.node_id &gt; 0 &amp;&amp; event.parent_mote_id &gt; 1 &amp;&amp; event.parent_mote_id != 65535) wsnMultihop = true;
    } catch(e) { log.log('PARSE_ERROR ' + line + '\n'); }
  }
  YIELD();
}</script>
      <active>true</active>
    </plugin_config>
  </plugin>
</simconf>