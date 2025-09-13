"""
Custom ML Models for Document Intelligence
Advanced machine learning models for document classification, sentiment analysis, and content extraction
"""

import asyncio
import logging
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
from transformers import TrainingArguments, Trainer
import onnxruntime as ort

from ...shared.config.settings import config_manager
from ...shared.events.event_sourcing import DomainEvent, EventType, EventBus

class DocumentDataset(Dataset):
    """PyTorch dataset for document classification"""
    
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

class DocumentClassificationModel(nn.Module):
    """Neural network for document classification"""
    
    def __init__(self, num_classes, model_name='bert-base-uncased'):
        super(DocumentClassificationModel, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        output = self.dropout(pooled_output)
        return self.classifier(output)

class MLModelManager:
    """Manages all ML models for document intelligence"""
    
    def __init__(self, event_bus: EventBus = None):
        self.config = config_manager.get_azure_config()
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # Model storage
        self.models = {}
        self.vectorizers = {}
        self.label_encoders = {}
        
        # Document types for classification
        self.document_types = [
            'invoice', 'receipt', 'contract', 'report', 'correspondence',
            'technical', 'legal', 'medical', 'financial', 'other'
        ]
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all ML models"""
        try:
            # Document Classification Models
            self.models['document_classifier_tfidf'] = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2
            )
            
            self.models['document_classifier_count'] = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            self.models['sentiment_classifier'] = LogisticRegression(
                random_state=42,
                max_iter=1000,
                C=1.0
            )
            
            self.models['language_detector'] = MultinomialNB(alpha=0.1)
            
            # Vectorizers
            self.vectorizers['tfidf'] = TfidfVectorizer(
                max_features=10000,
                stop_words='english',
                ngram_range=(1, 3),
                min_df=2,
                max_df=0.95
            )
            
            self.vectorizers['count'] = CountVectorizer(
                max_features=10000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.95
            )
            
            # Label encoders
            self.label_encoders['document_type'] = LabelEncoder()
            self.label_encoders['sentiment'] = LabelEncoder()
            self.label_encoders['language'] = LabelEncoder()
            
            # Initialize with known labels
            self.label_encoders['document_type'].fit(self.document_types)
            self.label_encoders['sentiment'].fit(['positive', 'negative', 'neutral'])
            self.label_encoders['language'].fit(['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko'])
            
            self.logger.info("ML models initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing ML models: {str(e)}")
            raise
    
    async def train_document_classifier(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train document classification model"""
        try:
            self.logger.info(f"Training document classifier with {len(training_data)} samples")
            
            # Prepare training data
            texts = [doc['content'] for doc in training_data]
            labels = [doc['document_type'] for doc in training_data]
            
            # Encode labels
            encoded_labels = self.label_encoders['document_type'].transform(labels)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                texts, encoded_labels, test_size=0.2, random_state=42, stratify=encoded_labels
            )
            
            # Vectorize text
            X_train_tfidf = self.vectorizers['tfidf'].fit_transform(X_train)
            X_test_tfidf = self.vectorizers['tfidf'].transform(X_test)
            
            X_train_count = self.vectorizers['count'].fit_transform(X_train)
            X_test_count = self.vectorizers['count'].transform(X_test)
            
            # Train TF-IDF model
            self.models['document_classifier_tfidf'].fit(X_train_tfidf, y_train)
            tfidf_pred = self.models['document_classifier_tfidf'].predict(X_test_tfidf)
            tfidf_accuracy = accuracy_score(y_test, tfidf_pred)
            
            # Train Count model
            self.models['document_classifier_count'].fit(X_train_count, y_train)
            count_pred = self.models['document_classifier_count'].predict(X_test_count)
            count_accuracy = accuracy_score(y_test, count_pred)
            
            # Cross-validation scores
            tfidf_cv_scores = cross_val_score(
                self.models['document_classifier_tfidf'], 
                X_train_tfidf, y_train, cv=5
            )
            count_cv_scores = cross_val_score(
                self.models['document_classifier_count'], 
                X_train_count, y_train, cv=5
            )
            
            # Choose best model
            if tfidf_accuracy >= count_accuracy:
                best_model = 'document_classifier_tfidf'
                best_accuracy = tfidf_accuracy
                best_cv_scores = tfidf_cv_scores
            else:
                best_model = 'document_classifier_count'
                best_accuracy = count_accuracy
                best_cv_scores = count_cv_scores
            
            # Generate classification report
            y_pred = tfidf_pred if best_model == 'document_classifier_tfidf' else count_pred
            class_report = classification_report(
                y_test, y_pred, 
                target_names=self.label_encoders['document_type'].classes_,
                output_dict=True
            )
            
            training_result = {
                'model_name': best_model,
                'accuracy': best_accuracy,
                'cv_mean': best_cv_scores.mean(),
                'cv_std': best_cv_scores.std(),
                'classification_report': class_report,
                'training_samples': len(training_data),
                'test_samples': len(X_test),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Save model
            await self._save_model(best_model, training_result)
            
            self.logger.info(f"Document classifier training completed. Accuracy: {best_accuracy:.4f}")
            return training_result
            
        except Exception as e:
            self.logger.error(f"Error training document classifier: {str(e)}")
            raise
    
    async def train_sentiment_classifier(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train sentiment analysis model"""
        try:
            self.logger.info(f"Training sentiment classifier with {len(training_data)} samples")
            
            # Prepare training data
            texts = [doc['content'] for doc in training_data]
            sentiments = [doc['sentiment'] for doc in training_data]
            
            # Encode labels
            encoded_sentiments = self.label_encoders['sentiment'].transform(sentiments)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                texts, encoded_sentiments, test_size=0.2, random_state=42, stratify=encoded_sentiments
            )
            
            # Vectorize text
            X_train_tfidf = self.vectorizers['tfidf'].fit_transform(X_train)
            X_test_tfidf = self.vectorizers['tfidf'].transform(X_test)
            
            # Train model
            self.models['sentiment_classifier'].fit(X_train_tfidf, y_train)
            y_pred = self.models['sentiment_classifier'].predict(X_test_tfidf)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            cv_scores = cross_val_score(
                self.models['sentiment_classifier'], 
                X_train_tfidf, y_train, cv=5
            )
            
            class_report = classification_report(
                y_test, y_pred,
                target_names=self.label_encoders['sentiment'].classes_,
                output_dict=True
            )
            
            training_result = {
                'model_name': 'sentiment_classifier',
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'classification_report': class_report,
                'training_samples': len(training_data),
                'test_samples': len(X_test),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Save model
            await self._save_model('sentiment_classifier', training_result)
            
            self.logger.info(f"Sentiment classifier training completed. Accuracy: {accuracy:.4f}")
            return training_result
            
        except Exception as e:
            self.logger.error(f"Error training sentiment classifier: {str(e)}")
            raise
    
    async def train_language_detector(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train language detection model"""
        try:
            self.logger.info(f"Training language detector with {len(training_data)} samples")
            
            # Prepare training data
            texts = [doc['content'] for doc in training_data]
            languages = [doc['language'] for doc in training_data]
            
            # Encode labels
            encoded_languages = self.label_encoders['language'].transform(languages)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                texts, encoded_languages, test_size=0.2, random_state=42, stratify=encoded_languages
            )
            
            # Vectorize text
            X_train_count = self.vectorizers['count'].fit_transform(X_train)
            X_test_count = self.vectorizers['count'].transform(X_test)
            
            # Train model
            self.models['language_detector'].fit(X_train_count, y_train)
            y_pred = self.models['language_detector'].predict(X_test_count)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            cv_scores = cross_val_score(
                self.models['language_detector'], 
                X_train_count, y_train, cv=5
            )
            
            class_report = classification_report(
                y_test, y_pred,
                target_names=self.label_encoders['language'].classes_,
                output_dict=True
            )
            
            training_result = {
                'model_name': 'language_detector',
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'classification_report': class_report,
                'training_samples': len(training_data),
                'test_samples': len(X_test),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Save model
            await self._save_model('language_detector', training_result)
            
            self.logger.info(f"Language detector training completed. Accuracy: {accuracy:.4f}")
            return training_result
            
        except Exception as e:
            self.logger.error(f"Error training language detector: {str(e)}")
            raise
    
    async def classify_document(self, text: str) -> Dict[str, Any]:
        """Classify document type using trained models"""
        try:
            # Use TF-IDF model for classification
            text_vectorized = self.vectorizers['tfidf'].transform([text])
            
            # Get prediction probabilities
            probabilities = self.models['document_classifier_tfidf'].predict_proba(text_vectorized)[0]
            
            # Get predicted class
            predicted_class_idx = np.argmax(probabilities)
            predicted_class = self.label_encoders['document_type'].classes_[predicted_class_idx]
            confidence = probabilities[predicted_class_idx]
            
            # Get top 3 predictions
            top_indices = np.argsort(probabilities)[-3:][::-1]
            top_predictions = []
            
            for idx in top_indices:
                top_predictions.append({
                    'class': self.label_encoders['document_type'].classes_[idx],
                    'confidence': float(probabilities[idx])
                })
            
            return {
                'predicted_type': predicted_class,
                'confidence': float(confidence),
                'top_predictions': top_predictions,
                'model_used': 'document_classifier_tfidf',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error classifying document: {str(e)}")
            raise
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using trained model"""
        try:
            # Vectorize text
            text_vectorized = self.vectorizers['tfidf'].transform([text])
            
            # Get prediction probabilities
            probabilities = self.models['sentiment_classifier'].predict_proba(text_vectorized)[0]
            
            # Get predicted sentiment
            predicted_sentiment_idx = np.argmax(probabilities)
            predicted_sentiment = self.label_encoders['sentiment'].classes_[predicted_sentiment_idx]
            confidence = probabilities[predicted_sentiment_idx]
            
            # Get all sentiment scores
            sentiment_scores = {}
            for i, sentiment in enumerate(self.label_encoders['sentiment'].classes_):
                sentiment_scores[sentiment] = float(probabilities[i])
            
            return {
                'predicted_sentiment': predicted_sentiment,
                'confidence': float(confidence),
                'sentiment_scores': sentiment_scores,
                'model_used': 'sentiment_classifier',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            raise
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect document language using trained model"""
        try:
            # Vectorize text
            text_vectorized = self.vectorizers['count'].transform([text])
            
            # Get prediction probabilities
            probabilities = self.models['language_detector'].predict_proba(text_vectorized)[0]
            
            # Get predicted language
            predicted_lang_idx = np.argmax(probabilities)
            predicted_language = self.label_encoders['language'].classes_[predicted_lang_idx]
            confidence = probabilities[predicted_lang_idx]
            
            # Get top 3 language predictions
            top_indices = np.argsort(probabilities)[-3:][::-1]
            top_predictions = []
            
            for idx in top_indices:
                top_predictions.append({
                    'language': self.label_encoders['language'].classes_[idx],
                    'confidence': float(probabilities[idx])
                })
            
            return {
                'predicted_language': predicted_language,
                'confidence': float(confidence),
                'top_predictions': top_predictions,
                'model_used': 'language_detector',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting language: {str(e)}")
            raise
    
    async def batch_predict(self, texts: List[str], prediction_type: str = 'all') -> List[Dict[str, Any]]:
        """Perform batch predictions on multiple texts"""
        try:
            results = []
            
            for text in texts:
                result = {'text': text}
                
                if prediction_type in ['all', 'classification']:
                    classification = await self.classify_document(text)
                    result['classification'] = classification
                
                if prediction_type in ['all', 'sentiment']:
                    sentiment = await self.analyze_sentiment(text)
                    result['sentiment'] = sentiment
                
                if prediction_type in ['all', 'language']:
                    language = await self.detect_language(text)
                    result['language'] = language
                
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch prediction: {str(e)}")
            raise
    
    async def _save_model(self, model_name: str, training_result: Dict[str, Any]):
        """Save trained model to storage"""
        try:
            # Save model
            model_path = f"models/{model_name}.joblib"
            joblib.dump(self.models[model_name], model_path)
            
            # Save vectorizer if applicable
            if 'tfidf' in model_name:
                vectorizer_path = f"models/{model_name}_vectorizer.joblib"
                joblib.dump(self.vectorizers['tfidf'], vectorizer_path)
            elif 'count' in model_name:
                vectorizer_path = f"models/{model_name}_vectorizer.joblib"
                joblib.dump(self.vectorizers['count'], vectorizer_path)
            
            # Save label encoder
            encoder_path = f"models/{model_name}_encoder.joblib"
            if 'document' in model_name:
                joblib.dump(self.label_encoders['document_type'], encoder_path)
            elif 'sentiment' in model_name:
                joblib.dump(self.label_encoders['sentiment'], encoder_path)
            elif 'language' in model_name:
                joblib.dump(self.label_encoders['language'], encoder_path)
            
            # Save training metadata
            metadata_path = f"models/{model_name}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(training_result, f, indent=2)
            
            self.logger.info(f"Model {model_name} saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving model {model_name}: {str(e)}")
            raise
    
    async def load_model(self, model_name: str):
        """Load trained model from storage"""
        try:
            # Load model
            model_path = f"models/{model_name}.joblib"
            self.models[model_name] = joblib.load(model_path)
            
            # Load vectorizer if applicable
            if 'tfidf' in model_name:
                vectorizer_path = f"models/{model_name}_vectorizer.joblib"
                self.vectorizers['tfidf'] = joblib.load(vectorizer_path)
            elif 'count' in model_name:
                vectorizer_path = f"models/{model_name}_vectorizer.joblib"
                self.vectorizers['count'] = joblib.load(vectorizer_path)
            
            # Load label encoder
            encoder_path = f"models/{model_name}_encoder.joblib"
            if 'document' in model_name:
                self.label_encoders['document_type'] = joblib.load(encoder_path)
            elif 'sentiment' in model_name:
                self.label_encoders['sentiment'] = joblib.load(encoder_path)
            elif 'language' in model_name:
                self.label_encoders['language'] = joblib.load(encoder_path)
            
            self.logger.info(f"Model {model_name} loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading model {model_name}: {str(e)}")
            raise