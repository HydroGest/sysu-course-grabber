<template>
  <v-app>
    <v-app-bar app color="surface" elevation="0" border class="app-bar">
      <template #prepend>
        <v-app-bar-nav-icon v-if="isMobile" @click="drawer = !drawer" />
      </template>
      <v-app-bar-title>
        <div class="d-flex align-center ga-2">
          <v-avatar color="primary" size="32" variant="flat" rounded="lg">
            <v-icon color="white" size="18">mdi-school</v-icon>
          </v-avatar>
          <span class="text-h6 font-weight-bold app-name">SYSU 抢课助手</span>
        </div>
      </v-app-bar-title>
      <v-spacer />
      <v-chip
        size="small"
        variant="flat"
        :color="cookieColor"
        class="mr-2"
      >
        <v-icon start size="16">
          {{ cookieText === '登录已失效' ? 'mdi-alert-circle' : cookieOk ? 'mdi-check-circle' : 'mdi-login' }}
        </v-icon>
        {{ cookieText }}
      </v-chip>
      <v-chip
        size="small"
        variant="flat"
        :color="health && health.engine ? 'primary' : 'error'"
        class="mr-3"
      >
        <v-icon start size="16">mdi-engine-outline</v-icon>
        {{ engineText }}
      </v-chip>
      <v-btn variant="text" prepend-icon="mdi-refresh" @click="refreshStage" title="刷新阶段">
        刷新阶段
      </v-btn>
      <v-btn
        variant="text"
        :color="cookieOk ? '' : 'primary'"
        prepend-icon="mdi-account-key-outline"
        @click="openGuide"
      >
        登录设置
      </v-btn>
      <v-btn variant="text" color="error" prepend-icon="mdi-power" @click="quitApp">
        退出
      </v-btn>
    </v-app-bar>

    <v-navigation-drawer
      v-model="drawer"
      app
      :permanent="!isMobile"
      width="248"
      color="surface"
      elevation="0"
      class="side-drawer"
    >
      <v-list nav density="comfortable" class="pa-2">
        <v-list-item
          v-for="item in navItems"
          :key="item.view"
          :prepend-icon="item.icon"
          :title="item.title"
          :active="view === item.view"
          rounded="lg"
          class="mb-1 nav-item"
          @click="switchView(item.view)"
        />
      </v-list>
    </v-navigation-drawer>

    <v-main class="app-main">
      <v-container fluid class="page-content">
          <template v-if="view === 'home'">
            <v-row class="mb-2 align-center">
              <v-col>
                <div class="text-h5 font-weight-bold">总览</div>
              </v-col>
              <v-col cols="auto">
                <v-btn
                  v-if="!cookieOk"
                  color="primary"
                  prepend-icon="mdi-login-variant"
                  @click="openGuide"
                >
                  去登录
                </v-btn>
                <v-btn
                  v-else-if="targets.length === 0"
                  color="primary"
                  prepend-icon="mdi-magnify"
                  @click="goSearch"
                >
                  搜索课程
                </v-btn>
                <v-btn v-else color="primary" prepend-icon="mdi-target" @click="goTargets">
                  抢课目标
                </v-btn>
              </v-col>
            </v-row>

            <v-row class="mb-2">
              <v-col cols="6" sm="3">
                <v-card>
                  <v-card-text>
                    <div class="text-overline text-medium-emphasis">登录状态</div>
                    <div class="text-h6 font-weight-bold mt-1" :class="cookieText === '已登录' ? 'text-success' : cookieText === '登录已失效' ? 'text-error' : 'text-warning'">
                      {{ cookieText }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="6" sm="3">
                <v-card>
                  <v-card-text>
                    <div class="text-overline text-medium-emphasis">选课阶段</div>
                    <div class="text-h6 font-weight-bold mt-1">{{ stageText }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="6" sm="3">
                <v-card>
                  <v-card-text>
                    <div class="text-overline text-medium-emphasis">运行中</div>
                    <div class="text-h6 font-weight-bold mt-1">{{ runningCount }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="6" sm="3">
                <v-card>
                  <v-card-text>
                    <div class="text-overline text-medium-emphasis">已完成</div>
                    <div class="text-h6 font-weight-bold mt-1 text-success">{{ doneCount }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <v-card class="mb-4">
              <v-toolbar flat color="surface">
                <v-toolbar-title class="text-subtitle-1">当前任务</v-toolbar-title>
                <v-spacer />
                <v-btn variant="text" size="small" @click="goTargets">查看全部</v-btn>
              </v-toolbar>
              <v-table density="compact" v-if="targets.length">
                <thead>
                  <tr>
                    <th>目标</th>
                    <th>状态</th>
                    <th>尝试</th>
                    <th>最近结果</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="t in targets.slice(0, 6)" :key="t.id">
                    <td>
                      <strong>{{ t.name }}</strong>
                      <div class="text-caption text-medium-emphasis">{{ courseLine(t) }}</div>
                    </td>
                    <td><v-chip size="small" :color="statusColor(t.status)">{{ statusText(t.status) }}</v-chip></td>
                    <td>{{ t.attempts }}</td>
                    <td class="text-caption">{{ t.last_message || '-' }}</td>
                  </tr>
                </tbody>
              </v-table>
              <v-card-text v-else class="text-center">
                <v-btn v-if="cookieOk" color="primary" prepend-icon="mdi-magnify" @click="goSearch">
                  搜索课程
                </v-btn>
                <v-btn v-else color="primary" prepend-icon="mdi-login-variant" @click="openGuide">
                  去登录
                </v-btn>
              </v-card-text>
            </v-card>

            <v-card>
              <v-toolbar flat color="surface">
                <v-toolbar-title class="text-subtitle-1">运行记录</v-toolbar-title>
              </v-toolbar>
              <v-list v-if="logs.length" density="compact">
                <v-list-item
                  v-for="log in logs.slice(-10).reverse()"
                  :key="log.id"
                  :title="log.message"
                  rounded="xl"
                  class="mb-1 log-row"
                >
                  <template #prepend>
                    <v-avatar :color="logColor(log.level)" variant="tonal" size="34" rounded="lg">
                      <v-icon size="20">{{ logIcon(log.level) }}</v-icon>
                    </v-avatar>
                  </template>
                  <template #subtitle>
                    <span class="text-caption text-medium-emphasis">
                      {{ log.ts }} · {{ log.source }}
                    </span>
                  </template>
                </v-list-item>
              </v-list>
              <v-card-text v-else class="text-center text-medium-emphasis">暂无记录</v-card-text>
            </v-card>
          </template>

          <template v-else-if="view === 'search'">
            <div class="text-h5 font-weight-bold mb-4">搜索课程</div>
            <v-card class="mb-3">
              <v-card-text>
                <v-row align="center">
                  <v-col cols="12" sm="6" md="7">
                    <v-text-field
                      ref="searchInput"
                      v-model="searchQ"
                      label="课程号或课程名"
                      placeholder="输入后自动搜索"
                      clearable
                      prepend-inner-icon="mdi-magnify"
                      hide-details
                      @click:clear="doSearch"
                      @update:model-value="scheduleSearch"
                      @keyup.enter="doSearch"
                    />
                  </v-col>
                  <v-col cols="8" sm="4" md="3">
                    <v-select
                      v-model="searchType"
                      :items="scopeItems"
                      label="范围"
                      hide-details
                      @update:model-value="doSearch"
                    />
                  </v-col>
                  <v-col cols="4" sm="2">
                    <v-btn color="primary" block @click="doSearch">搜索</v-btn>
                  </v-col>
                </v-row>
              </v-card-text>
              <v-progress-linear v-if="searchLoading" indeterminate color="primary" />
            </v-card>

            <v-card>
              <v-table density="compact">
                <thead>
                  <tr>
                    <th>课程号</th>
                    <th>课程名</th>
                    <th>教学班</th>
                    <th>剩余</th>
                    <th>教师</th>
                    <th>时间地点</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in searchRows" :key="classKey(row)">
                    <td class="text-body-2">{{ row.courseNum || '-' }}</td>
                    <td>
                      <strong>{{ row.courseName }}</strong>
                      <div class="text-caption text-medium-emphasis">{{ row.teachingClassName || '' }}</div>
                    </td>
                    <td>{{ row.teachingClassNum || '-' }}</td>
                    <td>{{ row.remainNum ?? '-' }}</td>
                    <td class="text-body-2">
                      {{ teacherOf(row) }}
                    </td>
                    <td class="text-caption cell-wrap">
                      {{ row.teachingTimePlace || '-' }}
                      <div
                        v-for="conflict in (row.conflicts || [])"
                        :key="conflict"
                        class="conflict-line"
                      >
                        {{ conflict }}
                      </div>
                    </td>
                    <td>
                      <v-btn
                        v-if="!isCourseAdded(row)"
                        color="primary"
                        size="small"
                        variant="tonal"
                        prepend-icon="mdi-plus"
                        @click="addFromSearch(rowPayload(row), null)"
                      >
                        加入抢课目标
                      </v-btn>
                      <v-btn
                        v-else
                        size="small"
                        prepend-icon="mdi-target"
                        @click="goTargets"
                      >
                        查看目标
                      </v-btn>
                      <v-btn
                        v-if="!isCourseAdded(row)"
                        size="small"
                        prepend-icon="mdi-clock-outline"
                        class="ml-2"
                        @click="openSchedule(rowPayload(row))"
                      >
                        定时
                      </v-btn>
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <v-card-text
                v-if="searchDone && !searchRows.length"
                class="text-center text-medium-emphasis"
              >
                没有匹配结果
              </v-card-text>
            </v-card>
          </template>

          <template v-else-if="view === 'targets'">
            <div class="text-h5 font-weight-bold mb-3">抢课目标</div>
            <div class="mb-4">
              <v-btn prepend-icon="mdi-pencil-plus-outline" @click="openTargetDialog()">手动添加课程</v-btn>
              <v-btn prepend-icon="mdi-magnify" color="primary" class="ml-2" @click="goSearch">
                搜索课程
              </v-btn>
              <v-btn prepend-icon="mdi-play" class="ml-2" @click="startAllTargets">
                全部启动
              </v-btn>
              <v-btn prepend-icon="mdi-calendar-clock" class="ml-2" @click="openAllSchedule">
                全部定时启动
              </v-btn>
            </div>
            <v-card>
              <v-table density="comfortable">
                <thead>
                  <tr>
                    <th>目标</th>
                    <th>课程</th>
                    <th>状态</th>
                    <th>尝试</th>
                    <th>最近结果</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="t in targets" :key="t.id">
                    <td><strong>{{ t.name }}</strong></td>
                    <td class="text-caption">{{ courseLine(t) }}</td>
                    <td><v-chip size="small" :color="statusColor(t.status)">{{ statusText(t.status) }}</v-chip></td>
                    <td>
                      <v-chip size="x-small" variant="tonal">
                        尝试 {{ t.attempts }}
                      </v-chip>
                    </td>
                    <td class="text-caption cell-wrap">{{ t.last_message || '-' }}</td>
                    <td class="actions-cell">
                      <v-tooltip v-if="t.enabled" text="停止" location="top">
                        <template #activator="{ props }">
                          <v-btn v-bind="props" icon="mdi-stop" color="error" size="small" @click="targetAction(t, 'stop')" />
                        </template>
                      </v-tooltip>
                      <template v-else>
                        <v-tooltip text="定时启动" location="top">
                          <template #activator="{ props }">
                            <v-btn v-bind="props" icon="mdi-clock-outline" size="small" @click="openTargetSchedule(t)" />
                          </template>
                        </v-tooltip>
                        <v-tooltip text="试一次" location="top">
                          <template #activator="{ props }">
                            <v-btn v-bind="props" icon="mdi-lightning-bolt-outline" size="small" @click="targetAction(t, 'once')" />
                          </template>
                        </v-tooltip>
                        <v-tooltip text="开始抢课" location="top">
                          <template #activator="{ props }">
                            <v-btn
                              v-bind="props"
                              icon="mdi-play"
                              color="primary"
                              size="small"
                              class="ml-1"
                              @click="targetAction(t, 'start')"
                            />
                          </template>
                        </v-tooltip>
                      </template>
                      <v-tooltip text="编辑" location="top">
                        <template #activator="{ props }">
                          <v-btn v-bind="props" icon="mdi-pencil-outline" size="small" class="ml-1" @click="openTargetDialog(t)" />
                        </template>
                      </v-tooltip>
                      <v-tooltip text="删除" location="top">
                        <template #activator="{ props }">
                          <v-btn v-bind="props" icon="mdi-delete-outline" color="error" size="small" class="ml-1" @click="targetAction(t, 'delete')" />
                        </template>
                      </v-tooltip>
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <v-card-text v-if="!targets.length" class="text-center text-medium-emphasis">
                暂无目标
              </v-card-text>
            </v-card>
          </template>

          <template v-else-if="view === 'selected'">
            <div class="text-h5 font-weight-bold mb-3">已选课程</div>
            <v-card class="mb-3">
              <v-tabs v-model="selectedTab" color="primary" grow @update:model-value="onSelectedTab">
                <v-tab value="list">列表</v-tab>
                <v-tab value="schedule">课程表</v-tab>
              </v-tabs>

              <template v-if="selectedTab === 'list'">
                <v-toolbar flat color="surface">
                  <v-toolbar-title class="text-subtitle-1">
                    已选 {{ selectedRows.length }} 门 · {{ selectedSummary.credit }} 学分
                  </v-toolbar-title>
                  <v-spacer />
                  <v-btn variant="text" size="small" prepend-icon="mdi-refresh" @click="loadSelected">
                    刷新
                  </v-btn>
                </v-toolbar>
                <v-card-text v-if="selectedRows.length" class="pt-2">
                  <v-chip
                    v-for="part in categoryParts"
                    :key="part.text"
                    size="small"
                    class="mr-2 mb-1"
                    variant="tonal"
                  >
                    {{ part.text }}
                  </v-chip>
                </v-card-text>
                <v-progress-linear v-if="selectedLoading" indeterminate color="primary" />
                <v-table v-if="selectedRows.length" density="comfortable">
                  <thead>
                    <tr>
                      <th>课程号</th>
                      <th>课程</th>
                      <th>类别</th>
                      <th>学分</th>
                      <th>教学班</th>
                      <th>时间地点</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in selectedRows" :key="row.teachingClassId || row.courseNum">
                      <td class="text-body-2">{{ row.courseNum }}</td>
                      <td>
                        <strong>{{ row.courseName }}</strong>
                        <div class="text-caption text-medium-emphasis">{{ row.courseUnitName || '' }}</div>
                      </td>
                      <td>
                        <v-chip size="small" variant="tonal" color="secondary">
                          {{ categoryName(row) }}
                        </v-chip>
                      </td>
                      <td>{{ row.credit }}</td>
                      <td>{{ row.teachingClassNum }}</td>
                      <td class="text-caption cell-wrap">{{ row.teachingTimePlace || '-' }}</td>
                    </tr>
                  </tbody>
                </v-table>
                <v-card-text
                  v-else-if="!selectedLoading && cookieOk"
                  class="text-center text-medium-emphasis"
                >
                  暂无已选课程
                </v-card-text>
                <v-card-text v-else-if="!cookieOk" class="text-center">
                  <v-btn color="primary" prepend-icon="mdi-login-variant" @click="openGuide">
                    去登录
                  </v-btn>
                </v-card-text>
              </template>

              <template v-else>
                <v-toolbar flat color="surface">
                  <v-toolbar-title class="text-subtitle-1">
                    周课程表 · {{ scheduleEvents.length }} 个上课时段
                  </v-toolbar-title>
                  <v-spacer />
                  <v-btn variant="text" size="small" prepend-icon="mdi-refresh" @click="loadSchedule">
                    刷新
                  </v-btn>
                </v-toolbar>

                <v-alert
                  v-if="scheduleConflicts.length"
                  type="error"
                  variant="tonal"
                  class="mx-4 mt-3"
                >
                  <div class="font-weight-bold mb-1">时间冲突</div>
                  <div v-for="conflict in scheduleConflicts" :key="conflict.text" class="text-body-2">
                    {{ conflict.text }}
                  </div>
                </v-alert>

                <v-progress-linear v-if="scheduleLoading" indeterminate color="primary" />
                <div v-if="!cookieOk" class="text-center pa-8">
                  <v-btn color="primary" prepend-icon="mdi-login-variant" @click="openGuide">
                    去登录
                  </v-btn>
                </div>
                <v-table
                  v-else-if="scheduleEvents.length && !scheduleLoading"
                  density="comfortable"
                  class="schedule-table"
                >
                  <thead>
                    <tr>
                      <th>节次</th>
                      <th v-for="day in weekdays" :key="day.key">{{ day.text }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="section in 11" :key="section">
                      <td class="text-caption text-medium-emphasis">第 {{ section }} 节</td>
                      <td
                        v-for="day in weekdays"
                        :key="day.key + '-' + section"
                        class="schedule-cell"
                      >
                        <div
                          v-for="event in eventsForSlot(section, day.key)"
                          :key="event.course_num + event.weekday_text + event.section_text"
                          class="schedule-event"
                          :class="{ 'schedule-event-conflict': scheduleEventsForSlot(section, day.key).length > 1 }"
                        >
                          <div class="font-weight-medium text-body-2">{{ event.course_name }}</div>
                          <div class="text-caption text-medium-emphasis">{{ event.week_text }}</div>
                          <div class="text-caption text-medium-emphasis">{{ event.place }}</div>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
                <v-card-text v-else-if="!scheduleLoading" class="text-center text-medium-emphasis">
                  暂无课程表
                </v-card-text>
              </template>
            </v-card>
          </template>

          <template v-else-if="view === 'logs'">
            <div class="text-h5 font-weight-bold mb-3">运行记录</div>
            <div class="mb-3">
              <v-btn prepend-icon="mdi-delete-sweep-outline" @click="clearLogs">清空</v-btn>
            </div>
            <v-card>
              <v-list v-if="logs.length">
                <v-list-item
                  v-for="log in logs.slice().reverse()"
                  :key="log.id"
                  :title="log.message"
                  rounded="xl"
                  class="mb-1 log-row"
                >
                  <template #prepend>
                    <v-avatar :color="logColor(log.level)" variant="tonal" size="34" rounded="lg">
                      <v-icon size="20">{{ logIcon(log.level) }}</v-icon>
                    </v-avatar>
                  </template>
                  <template #subtitle>
                    <span class="text-caption text-medium-emphasis">
                      {{ log.ts }} · {{ log.source }}
                    </span>
                  </template>
                </v-list-item>
              </v-list>
              <v-card-text v-else class="text-center text-medium-emphasis">暂无记录</v-card-text>
            </v-card>
          </template>
        </v-container>
      </v-main>

    <v-dialog v-model="targetDialogOpen" max-width="720">
      <v-card>
        <v-card-title>{{ targetForm.id ? '编辑课程' : '新增课程' }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6">
              <v-text-field v-model="targetForm.courseName" label="课程名" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="targetForm.courseNum" label="课程号" />
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" sm="6">
              <v-select
                v-model="targetForm.selectedType"
                :items="typeItems"
                label="选课类型"
              />
            </v-col>
            <v-col cols="12" sm="6">
              <v-select v-model="targetForm.selectedCate" :items="cateItems" label="课程类别" />
            </v-col>
          </v-row>
          <v-text-field
            v-model="targetForm.clazzId"
            label="教学班 ID（选填，指定后不再搜索）"
            class="mb-2"
          />
          <v-checkbox v-model="targetForm.autoConfirm" label="自动二次确认" hide-details />
          <v-checkbox v-model="targetForm.once" label="只试一次" hide-details class="mt-n2" />
          <v-expansion-panels v-model="advancedPanels" variant="accordion" multiple class="mt-3">
            <v-expansion-panel value="advanced">
              <v-expansion-panel-title>高级设置</v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row class="pt-2">
                  <v-col cols="12" sm="4">
                    <v-text-field v-model.number="targetForm.priority" label="优先级" type="number" />
                  </v-col>
                  <v-col cols="12" sm="4">
                    <v-text-field v-model.number="targetForm.maxMinutes" label="最长抢课（分钟）" type="number" />
                  </v-col>
                  <v-col cols="12" sm="4">
                    <v-text-field v-model.number="targetForm.requestInterval" label="请求间隔（秒）" type="number" />
                  </v-col>
                </v-row>
                <v-text-field v-model="targetForm.startAt" label="开抢时间" type="datetime-local" />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="targetDialogOpen = false">取消</v-btn>
          <v-btn @click="saveTargetForm(false)">保存</v-btn>
          <v-btn color="primary" @click="saveTargetForm(true)">保存并启动</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="scheduleOpen" max-width="480">
      <v-card>
        <v-card-title>定时抢课</v-card-title>
        <v-card-text>
          <v-text-field v-model="scheduleAt" label="开抢时间" type="datetime-local" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="scheduleOpen = false">取消</v-btn>
          <v-btn color="primary" @click="scheduleSubmit">加入并到点抢</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="targetScheduleOpen" max-width="480">
      <v-card>
        <v-card-title>定时启动</v-card-title>
        <v-card-text>
          <v-text-field v-model="targetScheduleAt" label="开抢时间" type="datetime-local" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="targetScheduleOpen = false">取消</v-btn>
          <v-btn color="primary" @click="targetScheduleSubmit">设定并启动</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="guideOpen" max-width="560">
      <v-card>
        <v-card-title>登录设置</v-card-title>
        <v-card-text>
          <div class="d-flex align-center mb-4">
            <v-chip :color="cookieColor" class="mr-3">
              {{ cookieText }}
            </v-chip>
            <v-chip :color="loginStatusColor" class="mr-3">{{ loginStatusText }}</v-chip>
          </div>
          <div class="d-flex flex-wrap">
            <v-btn
              color="primary"
              prepend-icon="mdi-open-in-new"
              :disabled="['starting', 'waiting', 'captured'].includes(login.status)"
              @click="startBrowserLogin"
            >
              用浏览器登录
            </v-btn>
            <v-btn
              v-if="['starting', 'waiting', 'captured'].includes(login.status)"
              prepend-icon="mdi-close"
              class="ml-2"
              @click="cancelBrowserLogin"
            >
              取消等待
            </v-btn>
          </div>
          <v-expansion-panels variant="accordion" class="mt-4">
            <v-expansion-panel>
              <v-expansion-panel-title>浏览器扩展备用方案</v-expansion-panel-title>
              <v-expansion-panel-text>
                <p class="text-body-2 mb-2">{{ extensionDir }}</p>
                <v-btn variant="text" prepend-icon="mdi-open-in-new" @click="openExtensionsPage">
                  打开扩展页
                </v-btn>
                <v-btn variant="text" prepend-icon="mdi-content-copy" @click="copyExtensionPath">
                  复制扩展路径
                </v-btn>
                <v-textarea
                  v-model="manualCookie"
                  label="Cookie 高级回填"
                  rows="2"
                  class="mt-2"
                />
                <v-btn variant="tonal" @click="saveManualCookie">保存 Cookie</v-btn>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="guideOpen = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="2600">
      {{ snackbarText }}
    </v-snackbar>
  </v-app>
</template>

<script>
const statusLabels = {
  idle: "未启动",
  scheduled: "等待开抢",
  running: "抢课中",
  done: "已成功",
  aborted: "已停止",
  timeout: "已超时",
  needs_confirm: "需确认",
  no_cookie: "等待登录",
  error: "出错",
  tried: "已尝试",
};

const loginLabels = {
  idle: "等待登录",
  starting: "正在启动浏览器",
  waiting: "请在窗口登录",
  captured: "已捕获，正在保存",
  ready: "登录成功",
  closed: "窗口已关闭",
  error: "登录出错",
};

export default {
  data() {
    return {
      view: "home",
      drawer: true,
      isMobile: false,
      navItems: [
        { view: "home", title: "总览", icon: "mdi-view-dashboard-outline" },
        { view: "search", title: "搜索课程", icon: "mdi-magnify" },
        { view: "targets", title: "抢课目标", icon: "mdi-target" },
        { view: "selected", title: "已选课程", icon: "mdi-book-check-outline" },
        { view: "logs", title: "运行记录", icon: "mdi-format-list-bulleted" },
      ],
      scopeItems: [
        { title: "全部范围", value: "auto" },
        { title: "本专业", value: "1" },
        { title: "跨专业", value: "2" },
        { title: "体育", value: "3" },
        { title: "公选", value: "4" },
      ],
      typeItems: [
        { title: "本专业", value: "1" },
        { title: "跨专业", value: "2" },
        { title: "体育", value: "3" },
        { title: "公选", value: "4" },
      ],
      cateItems: [
        { title: "专必", value: "11" },
        { title: "专选", value: "21" },
        { title: "公选", value: "30" },
        { title: "公必", value: "10" },
      ],
      health: null,
      targets: [],
      logs: [],
      searchRows: [],
      selectedRows: [],
      selectedSummary: { course: 0, credit: 0 },
      selectedLoading: false,
      selectedTab: "list",
      scheduleEvents: [],
      scheduleConflicts: [],
      scheduleLoading: false,
      searchDone: false,
      searchLoading: false,
      searchQ: "",
      searchType: "auto",
      searchTimer: null,
      pollTimer: null,
      searchLeadDone: false,
      login: { status: "idle", message: "", error: "" },
      extensionDir: "",
      manualCookie: "",
      targetDialogOpen: false,
      advancedPanels: [],
      targetForm: {
        id: null,
        name: "",
        courseName: "",
        courseNum: "",
        clazzId: "",
        selectedType: "1",
        selectedCate: "11",
        priority: 100,
        maxMinutes: 60,
        requestInterval: 1.5,
        startAt: "",
        autoConfirm: true,
        once: false,
      },
      scheduleOpen: false,
      scheduleAt: "",
      schedulePayload: null,
      targetScheduleOpen: false,
      targetScheduleAt: "",
      targetScheduleId: null,
      guideOpen: false,
      autoGuideClose: false,
      snackbar: false,
      snackbarText: "",
      snackbarColor: "success",
    };
  },
  computed: {
    cookieOk() {
      return Boolean(this.health?.cookie && this.health.stage?.state === "ok");
    },
    cookieText() {
      const stage = this.health?.stage;
      if (this.health?.cookie && stage?.state === "ok") return "已登录";
      if (this.health?.cookie && stage?.state === "error") return "登录已失效";
      return "等待登录";
    },
    cookieColor() {
      if (this.cookieText === "已登录") return "success";
      if (this.cookieText === "登录已失效") return "error";
      return "warning";
    },
    engineText() {
      return this.health && this.health.engine ? "引擎运行中" : "引擎已停止";
    },
    stageText() {
      const stage = this.health?.stage || {};
      if (stage.state === "ok") {
        return [stage.stage_name, stage.semester].filter(Boolean).join(" · ");
      }
      if (stage.state === "no_cookie") return "等待登录";
      if (stage.state === "error") return "登录已失效";
      return "阶段未知";
    },
    runningCount() {
      return this.health?.targets?.running || 0;
    },
    doneCount() {
      return this.health?.targets?.done || 0;
    },
    loginStatusText() {
      return this.login.status === "ready"
        ? "登录成功"
        : (loginLabels[this.login.status] || this.login.status || "等待");
    },
    loginStatusColor() {
      if (this.login.status === "ready") return "success";
      if (["starting", "waiting", "captured"].includes(this.login.status)) return "primary";
      if (this.login.status === "error") return "error";
      return "default";
    },
    categoryParts() {
      const counts = {};
      for (const row of this.selectedRows) {
        const name = this.categoryName(row);
        counts[name] = (counts[name] || 0) + 1;
      }
      const order = ["公必", "专必", "专选", "公选", "荣誉课程", "跨专业"];
      return Object.entries(counts)
        .sort((a, b) => {
          const ia = order.indexOf(a[0]);
          const ib = order.indexOf(b[0]);
          return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
        })
        .map(([name, count]) => ({ text: `${name} ${count}` }));
    },
    weekdays() {
      return [
        { key: 1, text: "周一" },
        { key: 2, text: "周二" },
        { key: 3, text: "周三" },
        { key: 4, text: "周四" },
        { key: 5, text: "周五" },
        { key: 6, text: "周六" },
        { key: 7, text: "周日" },
      ];
    },
  },
  mounted() {
    this.isMobile = window.innerWidth < 900;
    window.addEventListener("resize", this.onResize);
    this.refreshAll();
    this.pollTimer = setInterval(this.refreshAll, 3000);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.onResize);
    clearInterval(this.pollTimer);
    clearTimeout(this.searchTimer);
  },
  methods: {
    onResize() {
      this.isMobile = window.innerWidth < 900;
    },
    toast(text, color = "success") {
      this.snackbarText = text;
      this.snackbarColor = color;
      this.snackbar = true;
    },
    async api(path, options = {}) {
      const opts = { headers: {}, ...options };
      if (opts.body) opts.headers["Content-Type"] = "application/json";
      const resp = await fetch(path, opts);
      let data = {};
      try { data = await resp.json(); } catch (_) { /* ignore */ }
      if (!resp.ok) {
        const e = new Error(data.message || data.error || `HTTP ${resp.status}`);
        e.data = data;
        throw e;
      }
      return data;
    },
    async refreshAll() {
      try {
        const [health, targetData, logData, loginData] = await Promise.all([
          this.api("/api/health"),
          this.api("/api/targets"),
          this.api("/api/logs?limit=80"),
          this.api("/api/session/login-status"),
        ]);
        this.health = health;
        this.targets = targetData.targets;
        this.logs = logData.logs;
        this.login = loginData;
      } catch (e) {
        this.health = null;
      }
      if (this.login.status === "ready" && this.autoGuideClose && this.guideOpen) {
        this.autoGuideClose = false;
        this.guideOpen = false;
        this.switchView("search");
      }
      if (this.cookieOk && this.targets.length === 0 && !this.searchLeadDone) {
        this.searchLeadDone = true;
        this.switchView("search");
      }
    },
    async refreshStage() {
      try {
        await this.api("/api/stage");
        this.toast("阶段信息已刷新");
        await this.refreshAll();
      } catch (e) {
        this.toast("刷新失败：" + e.message, "error");
      }
    },
    switchView(name) {
      this.view = name;
      if (name === "selected" && this.cookieOk) {
        this.loadSelected();
        if (this.selectedTab === "schedule") this.loadSchedule();
      }
      if (!this.isMobile) return;
      this.drawer = false;
      if (name === "search") this.$nextTick(() => this.$refs.searchInput?.focus());
    },
    goSearch() {
      this.switchView("search");
    },
    goTargets() {
      this.switchView("targets");
    },
    categoryName(row) {
      if (row.courseCategoryName) return row.courseCategoryName;
      return {
        "10": "公必",
        "11": "专必",
        "21": "专选",
        "30": "公选",
        "31": "荣誉课程",
        kzy: "跨专业",
      }[row.courseCateCode] || "其他";
    },
    logColor(level) {
      if (level === "error") return "error";
      if (level === "warn") return "warning";
      return "success";
    },
    logIcon(level) {
      if (level === "error") return "mdi-alert-circle-outline";
      if (level === "warn") return "mdi-alert-outline";
      return "mdi-information-outline";
    },
    teacherOf(row) {
      const direct = row.teachingStaffName || row.teachingTeacherName || row.teacher || "";
      if (direct.trim()) return direct.trim();
      const first = String(row.teachingTimePlace || "").split(/[,;，；]/)[0].trim();
      return first || "-";
    },
    async loadSelected() {
      if (!this.cookieOk) {
        this.selectedRows = [];
        return;
      }
      this.selectedLoading = true;
      try {
        const data = await this.api("/api/selected");
        this.selectedRows = data.rows || [];
        this.selectedSummary = data.summary || { course: 0, credit: 0 };
      } catch (e) {
        this.toast("已选课程刷新失败：" + e.message, "error");
      } finally {
        this.selectedLoading = false;
      }
    },
    onSelectedTab(tab) {
      if (tab === "schedule" && this.cookieOk) this.loadSchedule();
    },
    async loadSchedule() {
      if (!this.cookieOk) {
        this.scheduleEvents = [];
        this.scheduleConflicts = [];
        return;
      }
      this.scheduleLoading = true;
      try {
        const data = await this.api("/api/schedule");
        this.scheduleEvents = data.events || [];
        this.scheduleConflicts = data.conflicts || [];
      } catch (e) {
        this.toast("课程表刷新失败：" + e.message, "error");
      } finally {
        this.scheduleLoading = false;
      }
    },
    eventsForSlot(day, section) {
      return this.scheduleEvents.filter(
        (event) => event.weekday === day && event.start_section === section
      );
    },
    scheduleEventsForSlot(day, section) {
      return this.eventsForSlot(day, section);
    },
    statusText(status) {
      return statusLabels[status] || status || "-";
    },
    statusColor(status) {
      if (status === "done") return "success";
      if (["running", "scheduled"].includes(status)) return "primary";
      if (["no_cookie", "needs_confirm", "tried"].includes(status)) return "warning";
      if (["aborted", "timeout", "error"].includes(status)) return "error";
      return "default";
    },
    courseLine(t) {
      return [t.course_name, t.course_num].filter(Boolean).join(" · ") || "-";
    },
    scheduleSearch() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => this.doSearch(), 650);
    },
    async doSearch() {
      clearTimeout(this.searchTimer);
      this.searchLoading = true;
      this.searchRows = [];
      this.searchDone = false;
      try {
        const data = await this.api(
          `/api/search?q=${encodeURIComponent(this.searchQ)}&type=${encodeURIComponent(this.searchType)}`
        );
        this.searchRows = data.rows || [];
      } catch (e) {
        this.toast("搜索失败：" + e.message, "error");
        if (e.data?.error === "no_cookie") this.openGuide();
      } finally {
        this.searchDone = true;
        this.searchLoading = false;
      }
    },
    classKey(row) {
      return row.teachingClassId || row.clazzId || (row.courseNum + row.courseName);
    },
    rowPayload(row) {
      const type = row.searchType || this.searchType || "1";
      const cate = row.searchCate || { "1": "11", "2": "30", "3": "10", "4": "30" }[type] || "11";
      return {
        courseName: row.courseName,
        courseNum: row.courseNum,
        clazzId: row.teachingClassId || row.clazzId,
        name: `${row.courseName || ""} ${row.teachingClassNum || ""}`.trim(),
        selectedType: type,
        selectedCate: cate,
      };
    },
    isCourseAdded(row) {
      const clazz = row.teachingClassId || row.clazzId;
      const num = row.courseNum;
      return this.targets.some((t) =>
        (clazz && String(t.clazz_id) === String(clazz)) ||
        (!clazz && num && String(t.course_num) === String(num) && t.course_name === row.courseName)
      );
    },
    async addFromSearch(payload, startAt) {
      try {
        const body = { ...payload, startAt: startAt || null };
        const created = await this.api("/api/targets", { method: "POST", body: JSON.stringify(body) });
        if (startAt) {
          await this.api(`/api/targets/${created.id}/start`, {
            method: "POST",
            body: JSON.stringify({ mode: "auto" }),
          });
        }
        await this.refreshAll();
        this.switchView("targets");
        this.toast(startAt ? "已加入，到点自动开抢" : "已加入抢课目标");
      } catch (e) {
        this.toast("加入失败：" + e.message, "error");
      }
    },
    openSchedule(payload) {
      this.schedulePayload = payload;
      this.scheduleAt = "";
      this.scheduleOpen = true;
    },
    async scheduleSubmit() {
      if (!this.schedulePayload || !this.scheduleAt) return;
      const payload = this.schedulePayload;
      const startAt = this.scheduleAt;
      this.scheduleOpen = false;
      await this.addFromSearch(payload, startAt);
    },
    openTargetSchedule(target) {
      this.targetScheduleId = target.id;
      this.targetScheduleAt = this.toLocalInput(target.start_at);
      this.targetScheduleOpen = true;
    },
    openAllSchedule() {
      this.targetScheduleId = null;
      this.targetScheduleAt = "";
      this.targetScheduleOpen = true;
    },
    async targetScheduleSubmit() {
      if (!this.targetScheduleAt) return;
      try {
        if (this.targetScheduleId) {
          await this.scheduleTargetById(this.targetScheduleId, this.targetScheduleAt);
        } else {
          const candidates = this.targets.filter((t) =>
            ["idle", "tried", "needs_confirm", "no_cookie"].includes(t.status)
          );
          for (const t of candidates) {
            await this.scheduleTargetById(t.id, this.targetScheduleAt);
          }
          this.toast(`已设定 ${candidates.length} 个目标`);
        }
        this.targetScheduleOpen = false;
        if (this.targetScheduleId) this.toast("已设定，到点自动启动");
        await this.refreshAll();
      } catch (e) {
        this.toast("设定失败：" + e.message, "error");
      }
    },
    async scheduleTargetById(targetId, startAt) {
      await this.api(`/api/targets/${targetId}/update`, {
        method: "POST",
        body: JSON.stringify({ startAt }),
      });
      await this.api(`/api/targets/${targetId}/start`, {
        method: "POST",
        body: JSON.stringify({ mode: "auto" }),
      });
    },
    async targetAction(target, action) {
      try {
        if (action === "delete") {
          if (!confirm("删除该抢课目标？")) return;
          await this.api(`/api/targets/${target.id}/delete`, { method: "POST" });
          this.toast("已删除");
        } else if (action === "stop") {
          await this.api(`/api/targets/${target.id}/stop`, { method: "POST" });
          this.toast("已停止");
        } else if (action === "once") {
          await this.api(`/api/targets/${target.id}/once`, { method: "POST" });
          this.toast("已发送单次抢课请求");
        } else if (action === "start") {
          await this.api(`/api/targets/${target.id}/start`, {
            method: "POST",
            body: JSON.stringify({ mode: "auto" }),
          });
          this.toast("目标已启动");
        }
        await this.refreshAll();
      } catch (e) {
        this.toast("操作失败：" + e.message, "error");
      }
    },
    async startAllTargets() {
      const idle = this.targets.filter((t) => !t.enabled && !["done", "aborted", "timeout"].includes(t.status));
      for (const t of idle) {
        try {
          await this.api(`/api/targets/${t.id}/start`, {
            method: "POST",
            body: JSON.stringify({ mode: "auto" }),
          });
        } catch (_) { /* keep going */ }
      }
      this.toast("已启动 " + idle.length + " 个目标");
      await this.refreshAll();
    },
    resetTargetForm() {
      this.targetForm = {
        id: null, name: "", courseName: "", courseNum: "", clazzId: "",
        selectedType: "1", selectedCate: "11", priority: 100, maxMinutes: 60,
        requestInterval: 1.5, startAt: "", autoConfirm: true, once: false,
      };
      this.advancedPanels = [];
    },
    toLocalInput(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "";
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },
    openTargetDialog(target = null) {
      if (!target) {
        this.resetTargetForm();
      } else {
        this.targetForm = {
          id: target.id,
          name: target.name || "",
          courseName: target.course_name || "",
          courseNum: target.course_num || "",
          clazzId: target.clazz_id || "",
          selectedType: target.selected_type || "1",
          selectedCate: target.selected_cate || "11",
          priority: target.priority,
          maxMinutes: target.max_minutes,
          requestInterval: target.request_interval,
          startAt: this.toLocalInput(target.start_at),
          autoConfirm: target.auto_confirm,
          once: target.mode === "once",
        };
        this.advancedPanels = ["advanced"];
      }
      this.targetDialogOpen = true;
    },
    async saveTargetForm(startNow) {
      const form = this.targetForm;
      const data = {
        name: form.name || form.courseName || form.courseNum,
        courseName: form.courseName,
        courseNum: form.courseNum,
        clazzId: form.clazzId,
        selectedType: form.selectedType,
        selectedCate: form.selectedCate,
        priority: Number(form.priority || 100),
        maxMinutes: Number(form.maxMinutes || 60),
        requestInterval: Math.max(1, Number(form.requestInterval || 1.5)),
        startAt: form.startAt || null,
        autoConfirm: form.autoConfirm,
        mode: form.once ? "once" : "auto",
      };
      try {
        let id = form.id;
        if (id) {
          await this.api(`/api/targets/${id}/update`, { method: "POST", body: JSON.stringify(data) });
        } else {
          const created = await this.api("/api/targets", { method: "POST", body: JSON.stringify(data) });
          id = created.id;
        }
        if (startNow) {
          await this.api(`/api/targets/${id}/start`, {
            method: "POST",
            body: JSON.stringify({ mode: data.mode }),
          });
        }
        this.targetDialogOpen = false;
        this.toast(startNow ? "目标已启动" : "目标已保存");
        await this.refreshAll();
      } catch (e) {
        this.toast("保存失败：" + e.message, "error");
      }
    },
    async openGuide() {
      this.guideOpen = true;
      this.autoGuideClose = false;
      try {
        const data = await this.api("/api/context");
        this.extensionDir = data.extension_dir;
      } catch (_) { /* ignore */ }
    },
    async startBrowserLogin() {
      this.autoGuideClose = true;
      try {
        this.login = await this.api("/api/session/login", { method: "POST" });
      } catch (e) {
        this.toast("启动登录失败：" + e.message, "error");
      }
    },
    async cancelBrowserLogin() {
      this.autoGuideClose = false;
      try {
        await this.api("/api/session/cancel", { method: "POST" });
        this.login = { status: "idle", message: "", error: "" };
      } catch (e) {
        this.toast("取消失败：" + e.message, "error");
      }
    },
    openExtensionsPage() {
      this.api("/api/open/extensions", { method: "POST" });
    },
    async copyExtensionPath() {
      try {
        await navigator.clipboard.writeText(this.extensionDir);
        this.toast("扩展路径已复制");
      } catch (_) {
        this.toast("复制失败，请手动选择路径", "warning");
      }
    },
    async saveManualCookie() {
      const cookie = this.manualCookie.trim();
      if (!cookie) {
        this.toast("Cookie 为空", "error");
        return;
      }
      try {
        await this.api("/api/targets/0/paste-cookie", { method: "POST", body: JSON.stringify({ cookie }) });
        this.toast("Cookie 已保存");
        this.guideOpen = false;
        await this.refreshAll();
      } catch (e) {
        this.toast("保存失败：" + e.message, "error");
      }
    },
    async clearLogs() {
      if (!confirm("清空运行记录？")) return;
      await this.api("/api/logs/clear");
      await this.refreshAll();
    },
    async quitApp() {
      if (!confirm("退出抢课助手？")) return;
      try { await this.api("/api/shutdown", { method: "POST" }); } catch (_) { /* ignore */ }
      window.close();
    },
  },
};
</script>

<style scoped>
.app-main {
  background: rgb(var(--v-theme-background));
}
.page-content {
  max-width: 1280px;
  margin: 0 auto;
}
.app-bar {
  border-bottom: 1px solid rgb(var(--v-border-color), 0.5);
}
.side-drawer {
  border-right: 1px solid rgb(var(--v-border-color), 0.5);
}
:deep(.v-table) {
  background: transparent;
}
:deep(.v-table thead th) {
  color: #17231f;
  font-weight: 600;
  font-size: 12px;
  background: #f3f6f5;
}
:deep(.v-table tbody tr:hover) {
  background: rgb(var(--v-theme-primary), 0.04);
}
.log-row {
  border-radius: 10px;
}
.cell-wrap {
  max-width: 340px;
  white-space: normal;
  line-height: 1.45;
}
.schedule-table :deep(td) {
  min-width: 92px;
  vertical-align: top;
  height: 56px;
}
.schedule-cell {
  padding: 4px;
}
.schedule-event {
  background: rgb(var(--v-theme-primary), 0.08);
  border-left: 3px solid rgb(var(--v-theme-primary));
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 4px;
}
.schedule-event-conflict {
  background: rgb(var(--v-theme-error), 0.1);
  border-left-color: rgb(var(--v-theme-error));
}
.conflict-line {
  color: rgb(var(--v-theme-error));
  font-weight: 600;
  margin-top: 4px;
}
.actions-cell {
  white-space: nowrap;
}
@media (max-width: 720px) {
  .page-content {
    padding: 16px 12px;
  }
}
</style>
