/**
 * TEST: #done Command - Three-Phase Test
 *
 * PHASE 1: Normal - Agent CAN respond to messages
 * PHASE 2: After #done - Agent CANNOT respond (paused)
 * PHASE 3: After auto-resume - Agent STILL doesn't respond to cleared messages
 *
 * Expected runtime: ~65 seconds (includes 60-second auto-resume wait)
 */

import { MCPClientManager } from '@mcpjam/sdk';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

let monitorProcess = null;

function startMonitor() {
  console.log('Starting echo monitor for lunar_craft_128...');
  const configPath = join(projectRoot, 'configs', 'agents', 'lunar_craft_128.json');
  
  monitorProcess = spawn('uv', 
    ['run', 'python', '-m', 'ax_agent_studio.monitors.echo_monitor', 'lunar_craft_128', '--config', configPath],
    { cwd: projectRoot, stdio: ['ignore', 'pipe', 'pipe'] }
  );

  monitorProcess.stdout.on('data', (data) => {
    const output = data.toString();
    if (output.includes('Done:') || output.includes('PAUSED') || output.includes('⏸')) {
      console.log('[MONITOR]', output.trim());
    }
  });

  return monitorProcess;
}

function stopMonitor() {
  if (monitorProcess) {
    console.log('\nStopping monitor...');
    monitorProcess.kill('SIGTERM');
  }
}

process.on('exit', stopMonitor);
process.on('SIGINT', () => { stopMonitor(); process.exit(130); });

const config = {
  'lunar_craft_128': {
    command: 'npx', args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/lunar_craft_128',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  },
  'orion_344': {
    command: 'npx', args: ['-y', 'mcp-remote@0.1.29', 'http://localhost:8002/mcp/agents/orion_344',
           '--transport', 'http-only', '--allow-http', '--oauth-server', 'http://localhost:8001']
  }
};

async function main() {
  console.log('\n' + '='.repeat(80));
  console.log('TEST: #done Command - Three-Phase Validation');
  console.log('='.repeat(80));
  console.log('Phase 1: Agent responds normally (baseline)');
  console.log('Phase 2: After #done, agent stops responding (paused)');
  console.log('Phase 3: After auto-resume, agent still ignores cleared messages');
  console.log('='.repeat(80) + '\n');

  try {
    startMonitor();
    console.log('Waiting 5 seconds for monitor initialization...\n');
    await sleep(5000);

    const manager = new MCPClientManager(config, {
      defaultClientName: '#done Test',
      defaultClientVersion: '1.0.0'
    });

    // PHASE 1: Baseline
    console.log('='.repeat(80));
    console.log('PHASE 1: Normal Response (Baseline)');
    console.log('='.repeat(80));
    
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 test without done'
    });
    console.log('✓ Sent: "@lunar_craft_128 test without done"');
    await sleep(3000);

    const p1Check = await manager.executeTool('orion_344', 'messages', {
      action: 'check', since: '15m', limit: 20
    });

    const p1Response = (p1Check.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128' && m.content.includes('without done')
    );

    if (p1Response.length === 0) {
      console.log('❌ PHASE 1 FAILED: Agent did not respond\n');
      await cleanup(manager);
      process.exit(1);
    }
    console.log('✅ PHASE 1 PASSED: Agent responded normally\n');

    // PHASE 2: Send #done and verify no response to next message
    console.log('='.repeat(80));
    console.log('PHASE 2: Pause After #done');
    console.log('='.repeat(80));
    
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 message with done. #done'
    });
    console.log('✓ Sent: "@lunar_craft_128 message with done. #done"');
    await sleep(3000);

    // Now send another message - should NOT get response
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 message after done'
    });
    console.log('✓ Sent: "@lunar_craft_128 message after done"');
    console.log('Waiting 4 seconds for response...\n');
    await sleep(4000);

    const p2Check = await manager.executeTool('orion_344', 'messages', {
      action: 'check', since: '15m', limit: 40
    });

    const afterDoneResponse = (p2Check.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128' && m.content.includes('after done')
    );

    if (afterDoneResponse.length > 0) {
      console.log('❌ PHASE 2 FAILED: Agent responded while paused\n');
      await cleanup(manager);
      process.exit(1);
    }
    console.log('✅ PHASE 2 PASSED: Agent did NOT respond (correctly paused)\n');

    // PHASE 3: Wait for auto-resume and verify message was cleared
    console.log('='.repeat(80));
    console.log('PHASE 3: Message Clearing After Auto-Resume');
    console.log('='.repeat(80));
    console.log('Waiting 60 seconds for auto-resume...');
    console.log('(This verifies that the "message after done" was cleared)\n');
    await sleep(60000);

    // Send a NEW message to wake up the agent
    await manager.executeTool('orion_344', 'messages', {
      action: 'send',
      content: '@lunar_craft_128 new message after resume'
    });
    console.log('✓ Sent: "@lunar_craft_128 new message after resume"');
    await sleep(3000);

    const p3Check = await manager.executeTool('orion_344', 'messages', {
      action: 'check', since: '15m', limit: 60
    });

    // Agent should respond to NEW message but not the old "after done" message
    const newMessageResponse = (p3Check.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128' && m.content.includes('new message after resume')
    );

    const oldMessageResponse = (p3Check.messages || []).filter(m =>
      m.sender_name === 'lunar_craft_128' && m.content.includes('message after done')
    );

    if (newMessageResponse.length === 0) {
      console.log('❌ PHASE 3 FAILED: Agent did not respond to new message after resume\n');
      await cleanup(manager);
      process.exit(1);
    }

    if (oldMessageResponse.length > 0) {
      console.log('❌ PHASE 3 FAILED: Agent responded to cleared message (should have been deleted)\n');
      await cleanup(manager);
      process.exit(1);
    }

    console.log('✅ PHASE 3 PASSED: Messages were cleared, agent only responded to new messages\n');

    // SUCCESS
    console.log('='.repeat(80));
    console.log('FINAL RESULT: ALL TESTS PASSED ✅');
    console.log('='.repeat(80));
    console.log('✓ Phase 1: Normal messaging works');
    console.log('✓ Phase 2: #done triggers pause, agent stops responding');
    console.log('✓ Phase 3: Messages cleared, agent gets a real break');
    console.log('✓ Loop-breaking mechanism fully validated\n');
    console.log('='.repeat(80) + '\n');
    await cleanup(manager);
    process.exit(0);

  } catch (error) {
    console.error('\n✗ Test failed:', error.message);
    await cleanup(null);
    process.exit(1);
  }
}

async function cleanup(manager) {
  if (manager) {
    await manager.disconnectServer('lunar_craft_128');
    await manager.disconnectServer('orion_344');
  }
  stopMonitor();
  await sleep(1000);
}

main();
