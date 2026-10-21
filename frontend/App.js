import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, Animated } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';

const API = 'http://localhost:8000';

const TONES = [
  { id: 'support', label: '🧸 Бережная поддержка' },
  { id: 'push', label: '🔥 Дружеский пинок' },
  { id: 'zen', label: '🧘 Стоический дзен' },
  { id: 'humor', label: '😏 С легким юмором' },
];

const TAGS = ['Работа', 'Сон', 'Люди', 'Просто так'];

export default function App() {
  const [screen, setScreen] = useState('loading');
  const [name, setName] = useState('');
  const [tone, setTone] = useState('support');
  const [mood, setMood] = useState(null);
  const [reason, setReason] = useState(null);
  const [streak, setStreak] = useState(1);
  const [result, setResult] = useState('');
  const [fade] = useState(new Animated.Value(0));

  useEffect(() => {
    (async () => {
      const n = await AsyncStorage.getItem('name');
      const t = await AsyncStorage.getItem('tone');
      if (n) { setName(n); setTone(t || 'support'); setScreen('main'); }
      else setScreen('onboard');
    })();
  }, []);

  const saveOnboard = async () => {
    await AsyncStorage.setItem('name', name);
    await AsyncStorage.setItem('tone', tone);
    setScreen('main');
  };

  const openSettings = async () => {
    setScreen('onboard');
  };

  const ask = async (m, r) => {
    setMood(m);
    setReason(r);
    const tod = new Date().getHours();
    const bucket = tod < 6 ? 'ночь' : tod < 12 ? 'утро' : tod < 18 ? 'день' : 'вечер';
    try {
      const res = await axios.post(`${API}/api/motivate`, {
        name, tone, mood: m, reason: r, time_of_day: bucket, streak,
      });
      setResult(res.data.text);
    } catch (e) {
      setResult('Не удалось связаться с сервером.');
    }
    setScreen('result');
    fade.setValue(0);
    Animated.timing(fade, { toValue: 1, duration: 900, useNativeDriver: true }).start();
  };

  if (screen === 'loading') return <View style={s.container}><Text style={s.text}>Загрузка...</Text></View>;

  if (screen === 'onboard') {
    return (
      <ScrollView style={s.container} contentContainerStyle={s.center}>
        <Text style={s.title}>Как тебя зовут?</Text>
        <TextInput style={s.input} value={name} onChangeText={setName} placeholder="Имя" placeholderTextColor="#888" />
        <Text style={s.title}>Тон мотивации</Text>
        {TONES.map(t => (
          <TouchableOpacity key={t.id} style={[s.card, tone === t.id && s.cardActive]} onPress={() => setTone(t.id)}>
            <Text style={s.cardText}>{t.label}</Text>
          </TouchableOpacity>
        ))}
        <TouchableOpacity style={s.btn} onPress={saveOnboard}><Text style={s.btnText}>Сохранить и начать</Text></TouchableOpacity>
      </ScrollView>
    );
  }

  if (screen === 'main') {
    return (
      <View style={s.container}>
        <View style={s.header}>
          <Text style={s.greet}>Привет, {name} 👋</Text>
          <TouchableOpacity onPress={openSettings}><Text style={s.gear}>⚙️</Text></TouchableOpacity>
        </View>
        <Text style={s.question}>Какой сегодня заряд?</Text>
        <TouchableOpacity style={[s.bigBtn, {backgroundColor:'#f59e0b'}]} onPress={() => setScreen('tags_charged')}>
          <Text style={s.bigBtnText}>⚡ Заряжен на 100%</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[s.bigBtn, {backgroundColor:'#6366f1'}]} onPress={() => setScreen('tags_drained')}>
          <Text style={s.bigBtnText}>🪫 Батарейка на нуле</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === 'tags_charged' || screen === 'tags_drained') {
    const m = screen === 'tags_charged' ? 'charged' : 'drained';
    return (
      <View style={s.container}>
        <Text style={s.question}>Что повлияло?</Text>
        <View style={s.chips}>
          {TAGS.map(t => (
            <TouchableOpacity key={t} style={s.chip} onPress={() => ask(m, t)}>
              <Text style={s.chipText}>{t}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <TouchableOpacity style={s.skip} onPress={() => ask(m, null)}>
          <Text style={s.skipText}>Пропустить</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === 'result') {
    return (
      <View style={s.container}>
        <Animated.View style={[s.cardResult, {opacity: fade}]}>
          <Text style={s.resultText}>{result}</Text>
        </Animated.View>
        <View style={s.row}>
          <TouchableOpacity style={s.action} onPress={() => {}}><Text>❤️</Text></TouchableOpacity>
          <TouchableOpacity style={s.action} onPress={() => ask(mood, reason)}><Text>🔄</Text></TouchableOpacity>
          <TouchableOpacity style={s.action} onPress={() => setScreen('main')}><Text>Назад</Text></TouchableOpacity>
        </View>
      </View>
    );
  }

  return null;
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:'#0f172a', padding:20 },
  center: { alignItems:'center', paddingVertical:40 },
  title: { color:'#e2e8f0', fontSize:22, marginVertical:12, fontWeight:'600' },
  input: { width:'100%', backgroundColor:'#1e293b', color:'#fff', padding:14, borderRadius:12, fontSize:16, marginBottom:20 },
  card: { width:'100%', padding:16, backgroundColor:'#1e293b', borderRadius:12, marginVertical:6 },
  cardActive: { backgroundColor:'#334155', borderWidth:1, borderColor:'#818cf8' },
  cardText: { color:'#e2e8f0', fontSize:16 },
  btn: { marginTop:20, backgroundColor:'#818cf8', padding:16, borderRadius:12, width:'100%', alignItems:'center' },
  btnText: { color:'#fff', fontSize:16, fontWeight:'600' },
  header: { flexDirection:'row', justifyContent:'space-between', alignItems:'center', marginBottom:30 },
  greet: { color:'#e2e8f0', fontSize:20, fontWeight:'600' },
  gear: { fontSize:24 },
  question: { color:'#e2e8f0', fontSize:24, fontWeight:'700', marginBottom:30, textAlign:'center' },
  bigBtn: { padding:24, borderRadius:16, marginVertical:10, alignItems:'center' },
  bigBtnText: { color:'#fff', fontSize:18, fontWeight:'600' },
  chips: { flexDirection:'row', flexWrap:'wrap', justifyContent:'center', gap:10 },
  chip: { backgroundColor:'#1e293b', padding:14, borderRadius:20, margin:6 },
  chipText: { color:'#e2e8f0' },
  skip: { marginTop:30, alignSelf:'center' },
  skipText: { color:'#94a3b8' },
  cardResult: { backgroundColor:'#1e293b', padding:24, borderRadius:16, marginTop:40 },
  resultText: { color:'#e2e8f0', fontSize:17, lineHeight:26 },
  row: { flexDirection:'row', justifyContent:'space-around', marginTop:30 },
  action: { backgroundColor:'#334155', padding:16, borderRadius:12 },
  text: { color:'#fff' },
});
