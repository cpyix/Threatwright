// Library `icon` names (libraries/*/elements.yaml) mapped to bundled Lucide icons.
import BrickWall from '@lucide/svelte/icons/brick-wall'
import Box from '@lucide/svelte/icons/box'
import Cable from '@lucide/svelte/icons/cable'
import Cctv from '@lucide/svelte/icons/cctv'
import Cloud from '@lucide/svelte/icons/cloud'
import Cog from '@lucide/svelte/icons/cog'
import Cpu from '@lucide/svelte/icons/cpu'
import Database from '@lucide/svelte/icons/database'
import Fan from '@lucide/svelte/icons/fan'
import Gauge from '@lucide/svelte/icons/gauge'
import Key from '@lucide/svelte/icons/key'
import Laptop from '@lucide/svelte/icons/laptop'
import Microchip from '@lucide/svelte/icons/microchip'
import Monitor from '@lucide/svelte/icons/monitor'
import MonitorCog from '@lucide/svelte/icons/monitor-cog'
import Network from '@lucide/svelte/icons/network'
import OctagonAlert from '@lucide/svelte/icons/octagon-alert'
import Radio from '@lucide/svelte/icons/radio'
import Router from '@lucide/svelte/icons/router'
import ScrollText from '@lucide/svelte/icons/scroll-text'
import Server from '@lucide/svelte/icons/server'
import ServerCog from '@lucide/svelte/icons/server-cog'
import ShieldAlert from '@lucide/svelte/icons/shield-alert'
import ShieldCheck from '@lucide/svelte/icons/shield-check'
import Split from '@lucide/svelte/icons/split'
import Tablet from '@lucide/svelte/icons/tablet'
import Thermometer from '@lucide/svelte/icons/thermometer'
import Usb from '@lucide/svelte/icons/usb'
import User from '@lucide/svelte/icons/user'
import Wifi from '@lucide/svelte/icons/wifi'
import Workflow from '@lucide/svelte/icons/workflow'
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
