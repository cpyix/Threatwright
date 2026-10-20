// Library `icon` names (libraries/*/elements.yaml) mapped to bundled Lucide icons.
import Activity from '@lucide/svelte/icons/activity'
import ArrowBigRight from '@lucide/svelte/icons/arrow-big-right'
import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right'
import BatteryCharging from '@lucide/svelte/icons/battery-charging'
import Bot from '@lucide/svelte/icons/bot'
import Box from '@lucide/svelte/icons/box'
import BrickWall from '@lucide/svelte/icons/brick-wall'
import Building from '@lucide/svelte/icons/building'
import Cable from '@lucide/svelte/icons/cable'
import Cctv from '@lucide/svelte/icons/cctv'
import Cloud from '@lucide/svelte/icons/cloud'
import CloudUpload from '@lucide/svelte/icons/cloud-upload'
import Cog from '@lucide/svelte/icons/cog'
import Cpu from '@lucide/svelte/icons/cpu'
import Database from '@lucide/svelte/icons/database'
import Drill from '@lucide/svelte/icons/drill'
import Factory from '@lucide/svelte/icons/factory'
import Fan from '@lucide/svelte/icons/fan'
import FlaskConical from '@lucide/svelte/icons/flask-conical'
import Gamepad2 from '@lucide/svelte/icons/gamepad-2'
import Gauge from '@lucide/svelte/icons/gauge'
import Key from '@lucide/svelte/icons/key'
import Laptop from '@lucide/svelte/icons/laptop'
import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard'
import Merge from '@lucide/svelte/icons/merge'
import Microchip from '@lucide/svelte/icons/microchip'
import Monitor from '@lucide/svelte/icons/monitor'
import MonitorCheck from '@lucide/svelte/icons/monitor-check'
import MonitorCog from '@lucide/svelte/icons/monitor-cog'
import Network from '@lucide/svelte/icons/network'
import OctagonAlert from '@lucide/svelte/icons/octagon-alert'
import PackageCheck from '@lucide/svelte/icons/package-check'
import Radio from '@lucide/svelte/icons/radio'
import RadioReceiver from '@lucide/svelte/icons/radio-receiver'
import RadioTower from '@lucide/svelte/icons/radio-tower'
import Router from '@lucide/svelte/icons/router'
import Scan from '@lucide/svelte/icons/scan'
import ScanBarcode from '@lucide/svelte/icons/scan-barcode'
import ScrollText from '@lucide/svelte/icons/scroll-text'
import Server from '@lucide/svelte/icons/server'
import ServerCog from '@lucide/svelte/icons/server-cog'
import ShieldAlert from '@lucide/svelte/icons/shield-alert'
import ShieldCheck from '@lucide/svelte/icons/shield-check'
import ShieldPlus from '@lucide/svelte/icons/shield-plus'
import Siren from '@lucide/svelte/icons/siren'
import SlidersVertical from '@lucide/svelte/icons/sliders-vertical'
import SolarPanel from '@lucide/svelte/icons/solar-panel'
import Split from '@lucide/svelte/icons/split'
import Tablet from '@lucide/svelte/icons/tablet'
import Thermometer from '@lucide/svelte/icons/thermometer'
import Usb from '@lucide/svelte/icons/usb'
import User from '@lucide/svelte/icons/user'
import Users from '@lucide/svelte/icons/users'
import UtilityPole from '@lucide/svelte/icons/utility-pole'
import Wifi from '@lucide/svelte/icons/wifi'
import Workflow from '@lucide/svelte/icons/workflow'
import Zap from '@lucide/svelte/icons/zap'
import type { Component } from 'svelte'

const BY_NAME: Record<string, Component> = {
  plc: Cpu,
  'safety-plc': ShieldCheck,
  ipc: ServerCog,
  'soft-plc': Microchip,
  edge: Router,
  hmi: Monitor,
  workstation: MonitorCog,
  laptop: Laptop,
  tablet: Tablet,
  drive: Fan,
  io: Cable,
  sensor: Thermometer,
  camera: Cctv,
  'process-device': Gauge,
  switch: Network,
  firewall: BrickWall,
  wireless: Wifi,
  opcua: Workflow,
  mqtt: Radio,
  gateway: Split,
  server: Server,
  cloud: Cloud,
  key: Key,
  database: Database,
  log: ScrollText,
  'safety-output': ShieldAlert,
  estop: OctagonAlert,
  usb: Usb,
  dcs: Factory,
  sis: ShieldPlus,
  transmitter: Activity,
  valve: SlidersVertical,
  analyser: FlaskConical,
  multiplexer: Merge,
  scada: LayoutDashboard,
  'operator-station': MonitorCheck,
  mes: ArrowLeftRight,
  alarm: Siren,
  patch: PackageCheck,
  directory: Users,
  robot: Bot,
  pendant: Gamepad2,
  cnc: Drill,
  'safety-sensor': Scan,
  reader: ScanBarcode,
  rtu: UtilityPole,
  cellular: RadioTower,
  'iot-gateway': RadioReceiver,
  'cloud-connector': CloudUpload,
  diode: ArrowBigRight,
  meter: Zap,
  inverter: SolarPanel,
  battery: BatteryCharging,
  building: Building,
}

const BY_KIND: Record<string, Component> = {
  process: Cog,
  device: Box,
  datastore: Database,
  external: User,
}

export function iconFor(name: string | null | undefined, kind: string): Component {
  return (name && BY_NAME[name]) || BY_KIND[kind] || Box
}
