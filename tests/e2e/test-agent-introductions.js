#!/usr/bin/env node
/**
 * Simple test: Have each agent introduce themselves
 * This helps us see which agents are OAuth'd and working
 */

import { MCPClientManager } from '@mcpjam/sdk';

const AGENTS = ['ghost_ray_363', 'lunar_ray_510'];

const mcpConfig = {};
for (const agent of AGENTS) {
  mcpConfig[agent] = {
    command: 'npx',
    args: [
      '-y', 'mcp-remote@0.1.29',
      `http://localhost:8002/mcp/agents/${agent}`,
      '--transport', 'http-only',
      '--allow-http',
      '--oauth-server', 'http://localhost:8001'
    ]
  };
}

async function testAgentIntroductions() {
  console.log('\n' + '='.repeat(80));
  console.log('Agent Introduction Test');
  console.log('='.repeat(80));
  console.log('\nTesting agents:', AGENTS.join(', '));
  console.log('='.repeat(80));

  try {
    console.log('\nConnecting to agents via MCP JAM SDK...');
    const manager = new MCPClientManager(mcpConfig, {
      defaultClientName: 'E2E Test',
      defaultClientVersion: '1.0.0'
    });
    console.log('✓ Manager created');

    for (const agent of AGENTS) {
      console.log(`\n${'─'.repeat(80)}`);
      console.log(`Testing: ${agent}`);
      console.log('─'.repeat(80));

      try {
        const result = await manager.executeTool(agent, 'messages', {
          action: 'send',
          content: `Hello! I am ${agent} introducing myself for E2E testing.`
        });

        console.log(`✅ ${agent}: Message sent successfully!`);
        if (result.message_id) {
          console.log(`   Message ID: ${result.message_id.substring(0, 8)}`);
        }
      } catch (error) {
        console.log(`❌ ${agent}: FAILED`);
        console.log(`   Error: ${error.message}`);
      }
    }

    console.log('\n' + '='.repeat(80));
    console.log('Test Complete');
    console.log('='.repeat(80) + '\n');
    return true;

  } catch (error) {
    console.log('\n💥 ERROR:', error.message);
    console.log('='.repeat(80) + '\n');
    return false;
  }
}

testAgentIntroductions()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(error => {
    console.error('\n💥 Uncaught error:', error);
    process.exit(1);
  });
