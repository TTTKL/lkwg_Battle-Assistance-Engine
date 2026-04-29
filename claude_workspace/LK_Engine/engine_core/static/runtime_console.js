(function () {
  const $ = (id) => document.getElementById(id);

  const state = {
    sessionId: $("session-id").value.trim(),
  };

  function currentSessionId() {
    state.sessionId = $("session-id").value.trim();
    return state.sessionId;
  }

  function log(message, data) {
    const target = $("action-log");
    const stamp = new Date().toLocaleTimeString();
    const lines = [`[${stamp}] ${message}`];
    if (data !== undefined) {
      lines.push(JSON.stringify(data, null, 2));
    }
    target.textContent = `${lines.join("\n")}\n\n${target.textContent}`.trim();
  }

  async function callApi(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || data.message || "request_failed");
    }
    return data;
  }

  function csv(text) {
    return text.split(",").map((x) => x.trim()).filter(Boolean);
  }

  function renderReport(report, recommendation) {
    const summary = $("status-summary");
    const rec = $("recommendation");
    if (!report) {
      summary.textContent = "暂无报告";
      rec.textContent = "暂无推荐";
      return;
    }

    const chips = [];
    if (report.last_import_batch_id) {
      chips.push(`<span class="chip">最近校准 ${report.last_import_batch_id}</span>`);
    }
    if (report.has_manual_corrections) {
      chips.push(`<span class="chip danger">存在手动修正</span>`);
    }

    summary.innerHTML = `
      <div>${chips.join("")}</div>
      <div class="status-grid">
        <div class="status-card">
          <div class="meta">我方当前</div>
          <strong>${report.my_active_pet || "-"}</strong>
          <div>心数：${report.my_hearts ?? "-"}</div>
          <div>事件数：${report.event_count ?? 0}</div>
        </div>
        <div class="status-card">
          <div class="meta">敌方当前</div>
          <strong>${report.opponent_active_pet || "-"}</strong>
          <div>心数：${report.opponent_hearts ?? "-"}</div>
          <div>回合：${report.turn ?? 0}</div>
        </div>
      </div>
    `;

    if (!recommendation) {
      rec.textContent = "暂无推荐";
      return;
    }

    const bestAction = recommendation.best_action
      ? JSON.stringify(recommendation.best_action)
      : "暂无";
    const risks = (recommendation.risk_notes || []).slice(0, 3)
      .map((item) => `<li>${item}</li>`).join("");
    rec.innerHTML = `
      <div class="meta">当前推荐</div>
      <strong>${bestAction}</strong>
      <div>score=${recommendation.score ?? "-"} confidence=${recommendation.confidence ?? "-"}</div>
      <div>depth=${recommendation.analysis_depth ?? "-"} mode=${recommendation.inference_mode ?? "-"}</div>
      <ul>${risks || "<li>无</li>"}</ul>
    `;
  }

  function renderEvents(events) {
    const box = $("events-list");
    if (!events || !events.length) {
      box.className = "list empty";
      box.textContent = "暂无事件";
      return;
    }
    box.className = "list";
    box.innerHTML = events.slice(-12).reverse().map((event) => `
      <div class="list-item">
        <div><strong>${event.event_type}</strong> turn=${event.turn}</div>
        <div class="meta">event=${event.event_id}${event.import_batch_id ? ` batch=${event.import_batch_id}` : ""}</div>
        <div class="meta">${JSON.stringify(event.payload)}</div>
      </div>
    `).join("");
  }

  function renderImports(imports) {
    const box = $("imports-list");
    if (!imports || !imports.length) {
      box.className = "list empty";
      box.textContent = "暂无导入批次";
      return;
    }
    box.className = "list";
    box.innerHTML = imports.map((item) => `
      <div class="list-item">
        <div><strong>${item.import_batch_id}</strong></div>
        <div class="meta">turn=${item.turn} events=${item.event_count}</div>
        <div class="meta">${item.note || ""}</div>
      </div>
    `).join("");
  }

  async function refreshAll() {
    const sessionId = currentSessionId();
    if (!sessionId) {
      return;
    }
    const [reportData, eventsData, importsData] = await Promise.all([
      callApi(`/api/battle/${sessionId}/report`),
      callApi(`/api/battle/${sessionId}/events`),
      callApi(`/api/battle/${sessionId}/imports`),
    ]);
    renderReport(reportData.report, reportData.recommendation);
    renderEvents(eventsData.events);
    renderImports(importsData.imports);
  }

  async function appendEvent(eventType, payload, actorSide = null) {
    const sessionId = currentSessionId();
    const reportData = await callApi(`/api/battle/${sessionId}/event`, {
      method: "POST",
      body: JSON.stringify({
        turn: 1,
        event_type: eventType,
        payload,
        actor_side: actorSide,
      }),
    });
    renderReport(reportData.report, reportData.recommendation);
    log(`event ${eventType}`, reportData.event);
    await refreshLists();
  }

  async function refreshLists() {
    const sessionId = currentSessionId();
    const [eventsData, importsData] = await Promise.all([
      callApi(`/api/battle/${sessionId}/events`),
      callApi(`/api/battle/${sessionId}/imports`),
    ]);
    renderEvents(eventsData.events);
    renderImports(importsData.imports);
  }

  $("start-session").addEventListener("click", async () => {
    const payload = {
      session_id: currentSessionId(),
      my_team: csv($("my-team").value),
      opponent_team: csv($("opponent-team").value),
      search_depth: Number($("search-depth").value || 2),
      inference_mode: $("inference-mode").value,
    };
    try {
      const data = await callApi("/api/battle/start", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderReport(data.report, data.recommendation);
      await refreshLists();
      log("session started", payload);
    } catch (error) {
      log(`start failed: ${error.message}`);
    }
  });

  $("record-enemy-skill").addEventListener("click", async () => {
    try {
      await appendEvent("OPPONENT_ACTION_OBSERVED", {
        pet_name: $("enemy-skill-pet").value.trim(),
        skill_name: $("enemy-skill-name").value.trim(),
        action_type: "USE_SKILL",
      }, "opponent");
    } catch (error) {
      log(`record enemy skill failed: ${error.message}`);
    }
  });

  $("record-enemy-switch").addEventListener("click", async () => {
    try {
      await appendEvent("PET_SWITCHED", {
        side: "opponent",
        new_pet: $("enemy-switch-pet").value.trim(),
      });
    } catch (error) {
      log(`record switch failed: ${error.message}`);
    }
  });

  $("update-enemy-hp").addEventListener("click", async () => {
    try {
      await appendEvent("HP_PERCENT_UPDATED", {
        side: "opponent",
        pet_name: $("enemy-resource-pet").value.trim(),
        hp_percent: Number($("enemy-hp").value),
      });
    } catch (error) {
      log(`update hp failed: ${error.message}`);
    }
  });

  $("update-enemy-energy").addEventListener("click", async () => {
    try {
      await appendEvent("ENERGY_UPDATED", {
        side: "opponent",
        pet_name: $("enemy-resource-pet").value.trim(),
        energy: Number($("enemy-energy").value),
      });
    } catch (error) {
      log(`update energy failed: ${error.message}`);
    }
  });

  $("import-state").addEventListener("click", async () => {
    try {
      const sessionId = currentSessionId();
      const petName = $("import-active-pet").value.trim();
      const payload = {
        turn: 1,
        side: "opponent",
        active_pet_name: petName,
        pets: [{
          pet_name: petName,
          hp_percent: Number($("import-hp").value),
          energy: Number($("import-energy").value),
        }],
        note: $("import-note").value.trim(),
      };
      const data = await callApi(`/api/battle/${sessionId}/import_state`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderReport(data.report, data.recommendation);
      await refreshLists();
      $("rollback-import-id").value = data.import_batch_id;
      log("import snapshot", data);
    } catch (error) {
      log(`import failed: ${error.message}`);
    }
  });

  $("refresh-report").addEventListener("click", async () => {
    try {
      await refreshAll();
    } catch (error) {
      log(`refresh failed: ${error.message}`);
    }
  });

  $("undo-last").addEventListener("click", async () => {
    try {
      const sessionId = currentSessionId();
      const data = await callApi(`/api/battle/${sessionId}/undo`, { method: "POST" });
      renderReport(data.report, data.recommendation);
      await refreshLists();
      log("undo", data.removed_event);
    } catch (error) {
      log(`undo failed: ${error.message}`);
    }
  });

  $("clear-events").addEventListener("click", async () => {
    if (!window.confirm("确认清空当前事件信息？这会删除累计事件与推断结果，但保留会话配置。")) {
      return;
    }
    try {
      const sessionId = currentSessionId();
      const data = await callApi(`/api/battle/${sessionId}/clear_events`, {
        method: "POST",
        body: JSON.stringify({ confirm_text: "CLEAR" }),
      });
      renderReport(data.report, null);
      renderEvents([]);
      renderImports([]);
      log("events cleared", data);
    } catch (error) {
      log(`clear failed: ${error.message}`);
    }
  });

  $("rollback-import").addEventListener("click", async () => {
    try {
      const sessionId = currentSessionId();
      const importBatchId = $("rollback-import-id").value.trim();
      const data = await callApi(`/api/battle/${sessionId}/rollback_import/${importBatchId}`, {
        method: "POST",
      });
      renderReport(data.report, data.recommendation);
      await refreshLists();
      log("rollback import", data);
    } catch (error) {
      log(`rollback import failed: ${error.message}`);
    }
  });

  $("refresh-imports").addEventListener("click", async () => {
    try {
      const sessionId = currentSessionId();
      const data = await callApi(`/api/battle/${sessionId}/imports`);
      renderImports(data.imports);
    } catch (error) {
      log(`refresh imports failed: ${error.message}`);
    }
  });

  $("refresh-events").addEventListener("click", async () => {
    try {
      const sessionId = currentSessionId();
      const data = await callApi(`/api/battle/${sessionId}/events`);
      renderEvents(data.events);
    } catch (error) {
      log(`refresh events failed: ${error.message}`);
    }
  });

  $("clear-log").addEventListener("click", () => {
    $("action-log").textContent = "";
  });
})();
